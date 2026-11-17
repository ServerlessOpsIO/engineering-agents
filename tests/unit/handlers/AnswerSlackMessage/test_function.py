'''Test AnswerSlackMessage'''

import copy
import json
import os
import time
from types import ModuleType
from typing import Generator

import jsonschema
import pytest
from pytest_mock import MockerFixture

from common import agentcore
from common.agentcore import AgentFailed, AgentReply
from common.slack import text
from common.slack.errors import SlackUnavailable
from common.slack.thread import ThreadRead

FN_NAME = 'AnswerSlackMessage'
DATA_DIR = './data'
FUNC_DATA_DIR = os.path.join(DATA_DIR, 'handlers', FN_NAME)
EVENT = os.path.join(FUNC_DATA_DIR, 'event-mention.json')
EVENT_SCHEMA = os.path.join(FUNC_DATA_DIR, 'event.schema.json')
DATA = os.path.join(FUNC_DATA_DIR, 'data.json')
DATA_SCHEMA = os.path.join(FUNC_DATA_DIR, 'data.schema.json')

BOT = 'U0STRIDER'
CHANNEL = 'C0123ABCDEF'
# A word that appears in the sample message and nowhere else.
DISTINCTIVE_WORD = 'heron'
REPLY = 'A trust boundary is where **authority** changes hands. Remember the osprey.'
REPLY_WORD = 'osprey'
SECONDS_IN_A_DAY = 86400


def _load(path):
    with open(path) as f:
        return json.load(f)


def ts_ago(seconds: float = 1) -> str:
    return f'{time.time() - seconds:.6f}'


class FakeSlack:
    '''Stands in for common.slack.api. Records what was done, in order.'''

    def __init__(self):
        self.done = []
        self.member = True
        self.bot = BOT
        self.eyes_added = True
        self.eyes_removed = True
        self.posts_that_fail = set()

    def bot_user_id(self):
        if isinstance(self.bot, Exception):
            raise self.bot
        return self.bot

    def client(self):
        return 'a client'

    def is_full_member(self, user, team_id):
        self.done.append(('member?', user, team_id))
        if isinstance(self.member, Exception):
            raise self.member
        return self.member

    def add_eyes(self, channel, ts):
        self.done.append(('eyes on', channel, ts))
        return self.eyes_added

    def remove_eyes(self, channel, ts):
        self.done.append(('eyes off', channel, ts))
        return self.eyes_removed

    def post(self, channel, thread_ts, markdown):
        number = len(self.posts) + len(self.failed_posts) + 1
        if number in self.posts_that_fail or markdown in self.posts_that_fail:
            self.done.append(('post failed', channel, thread_ts, markdown))
            return False
        self.done.append(('post', channel, thread_ts, markdown))
        return True

    @property
    def posts(self):
        return [step[3] for step in self.done if step[0] == 'post']

    @property
    def failed_posts(self):
        return [step[3] for step in self.done if step[0] == 'post failed']

    @property
    def steps(self):
        return [step[0] for step in self.done]


class FakeAgent:
    '''Stands in for common.agentcore.ask. Gives its replies in turn.'''

    def __init__(self, *replies):
        self.replies = list(replies) or [AgentReply('answer', REPLY, 'agent-request-1')]
        self.asked = []

    def __call__(self, session_id, prompt, slack_user_id):
        self.asked.append({'session': session_id, 'prompt': prompt, 'user': slack_user_id})
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply


### Fixtures
@pytest.fixture()
def mock_context(lambda_function_context, function_name=FN_NAME):
    '''context object'''
    return lambda_function_context(function_name)


@pytest.fixture()
def mock_event() -> dict:
    '''An SQS event carrying one queued mention'''
    return _load(EVENT)


@pytest.fixture()
def slack() -> FakeSlack:
    return FakeSlack()


@pytest.fixture()
def agent() -> FakeAgent:
    return FakeAgent()


@pytest.fixture()
def thread(mocker):
    '''What reading the thread gives. Set .return_value or .side_effect.'''
    return mocker.patch(
        'src.handlers.AnswerSlackMessage.function.read_thread',
        return_value=ThreadRead(mentioned=True, answered_before=True, earlier=[]),
    )


@pytest.fixture()
def mock_fn(slack, agent, thread, monkeypatch, mocker: MockerFixture) -> Generator[ModuleType, None, None]:
    '''The function module with Slack and the agent replaced'''
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'test')
    monkeypatch.setenv('MAX_PROMPT_CHARS', '16000')
    monkeypatch.setenv('MEMORY_EXPIRY_DAYS', '7')

    import src.handlers.AnswerSlackMessage.function as fn

    mocker.patch('src.handlers.AnswerSlackMessage.function.api', slack)
    mocker.patch('src.handlers.AnswerSlackMessage.function.agentcore.ask', agent)
    mocker.patch('src.handlers.AnswerSlackMessage.function.time.sleep')
    yield fn


def event_with(mock_event: dict, **changes) -> dict:
    '''The SQS event with its queued message sent a moment ago and changed.'''
    event = copy.deepcopy(mock_event)
    data = json.loads(event['Records'][0]['body'])
    ts = ts_ago()
    data.update({'ts': ts, 'threadTs': ts})
    data.update(changes)
    event['Records'][0]['body'] = json.dumps(data)
    return event


def mention(mock_event, **changes):
    return event_with(mock_event, **changes)


def thread_reply(mock_event, **changes):
    fields = {'threadTs': ts_ago(600), 'isReply': True, 'channelType': 'channel',
              'eventType': 'message', 'text': f'and what about the {DISTINCTIVE_WORD}?'}
    fields.update(changes)
    return event_with(mock_event, **fields)


def direct_message(mock_event, **changes):
    fields = {'channel': 'D0123ABCDEF', 'channelType': 'im', 'eventType': 'message',
              'text': f'tell me about the {DISTINCTIVE_WORD}'}
    fields.update(changes)
    return event_with(mock_event, **fields)


def queued(event: dict) -> dict:
    return json.loads(event['Records'][0]['body'])


def last_record(caplog) -> dict:
    return vars(caplog.records[-1])


def outcome(caplog):
    record = last_record(caplog)
    return record['outcome'], record['reason']


def everything_logged(caplog, capsys) -> str:
    printed = capsys.readouterr()
    return '\n'.join([str(vars(record)) for record in caplog.records] + [printed.out, printed.err])


### Data validation
def test_validate_event(mock_event):
    '''Test the sample event against the schema'''
    jsonschema.validate(mock_event, _load(EVENT_SCHEMA))


def test_validate_data(mock_event):
    '''Test the queued message, in the event and on its own, against the schema'''
    schema = _load(DATA_SCHEMA)
    jsonschema.validate(_load(DATA), schema)
    jsonschema.validate(json.loads(mock_event['Records'][0]['body']), schema)


### A mention gets a reply (User Story 1)
def test_a_mention_is_answered_in_a_thread_with_the_eyes_on_while_it_works(
    mock_fn, mock_event, mock_context, slack, agent, thread, caplog
):
    event = mention(mock_event)
    data = queued(event)

    result = mock_fn.handler(event, mock_context)

    assert result == {'batchItemFailures': []}
    assert slack.steps == ['member?', 'eyes on', 'post', 'eyes off']
    assert slack.done[0] == ('member?', 'U0123ABCD', 'T0123ABCD')
    assert slack.done[1] == ('eyes on', CHANNEL, data['ts'])
    assert slack.done[2] == ('post', CHANNEL, data['ts'], REPLY)
    assert slack.done[3] == ('eyes off', CHANNEL, data['ts'])
    thread.assert_not_called()
    assert outcome(caplog) == ('answered', None)


def test_the_agent_gets_the_message_without_the_mention_and_the_threads_session(
    mock_fn, mock_event, mock_context, agent
):
    event = mention(mock_event, text=f'<@{BOT}> ask <@U0SOMEONE> about *this*')
    data = queued(event)

    mock_fn.handler(event, mock_context)

    [asked] = agent.asked
    assert asked['prompt'] == 'ask <@U0SOMEONE> about *this*'
    assert asked['user'] == 'U0123ABCD'
    assert asked['session'] == 'slack-T0123ABCD-C0123ABCDEF-' + data['ts'].replace('.', '-')


@pytest.mark.parametrize('membership, expected', [
    (False, ('declined', 'not_member')),
    (SlackUnavailable('ratelimited'), ('failed', 'membership_unknown')),
])
def test_someone_who_is_not_known_to_be_a_full_member_gets_nothing(
    mock_fn, mock_event, mock_context, slack, agent, caplog, membership, expected
):
    slack.member = membership

    result = mock_fn.handler(mention(mock_event), mock_context)

    assert result == {'batchItemFailures': []}
    assert slack.steps == ['member?']
    assert agent.asked == []
    assert outcome(caplog) == expected


def test_failing_to_add_the_eyes_does_not_stop_the_answer(mock_fn, mock_event, mock_context, slack, caplog):
    slack.eyes_added = False

    mock_fn.handler(mention(mock_event), mock_context)

    assert slack.posts == [REPLY]
    assert last_record(caplog)['reactionAdded'] is False
    assert outcome(caplog) == ('answered', None)


def test_failing_to_remove_the_eyes_is_logged_and_changes_nothing(mock_fn, mock_event, mock_context, slack, caplog):
    slack.eyes_removed = False

    mock_fn.handler(mention(mock_event), mock_context)

    assert last_record(caplog)['reactionRemoved'] is False
    assert outcome(caplog) == ('answered', None)


def test_the_log_record_joins_the_front_doors_record_and_the_agents(mock_fn, mock_event, mock_context, caplog):
    event = mention(mock_event)
    data = queued(event)

    mock_fn.handler(event, mock_context)

    record = last_record(caplog)
    assert record['correlationId'] == data['correlationId']
    assert record['agentRequestId'] == 'agent-request-1'
    assert record['sessionId'].startswith('slack-T0123ABCD-C0123ABCDEF-')
    assert record['eventId'] == 'Ev0123ABCD'
    assert (record['channel'], record['threadTs'], record['ts']) == (CHANNEL, data['threadTs'], data['ts'])
    assert record['user'] == 'U0123ABCD'
    assert record['attempts'] == 1
    assert record['threadRead'] is False
    assert (record['contextMessages'], record['contextDropped']) == (0, 0)
    assert record['replyParts'] == 1
    assert (record['reactionAdded'], record['reactionRemoved']) == (True, True)
    assert isinstance(record['durationMs'], int)


def test_no_message_text_and_no_reply_text_is_logged(mock_fn, mock_event, mock_context, slack, agent, caplog, capsys):
    mock_fn.handler(mention(mock_event), mock_context)
    agent.replies = [AgentFailed('RuntimeError')]
    mock_fn.handler(mention(mock_event), mock_context)

    logged = everything_logged(caplog, capsys)
    assert DISTINCTIVE_WORD not in logged
    assert 'trust boundary' not in logged
    assert REPLY_WORD not in logged


def test_a_long_reply_is_posted_in_labelled_parts_in_order(mock_fn, mock_event, mock_context, slack, agent, caplog):
    long_reply = '\n\n'.join(f'Paragraph {number}. ' + 'word ' * 150 for number in range(33))
    agent.replies = [AgentReply('answer', long_reply, 'r-1')]

    mock_fn.handler(mention(mock_event), mock_context)

    assert len(slack.posts) == 3
    assert [post.rsplit('\n\n', 1)[1] for post in slack.posts] == [
        '(part 1 of 3)', '(part 2 of 3)', '(part 3 of 3)'
    ]
    assert last_record(caplog)['replyParts'] == 3


### A conversation continues in its thread (User Story 4)
def test_a_reply_in_a_thread_where_strider_was_never_mentioned_gets_nothing(
    mock_fn, mock_event, mock_context, slack, agent, thread, caplog
):
    thread.return_value = ThreadRead(mentioned=False)

    mock_fn.handler(thread_reply(mock_event), mock_context)

    assert slack.done == []
    assert agent.asked == []
    assert outcome(caplog) == ('declined', 'not_strider_thread')
    assert last_record(caplog)['threadRead'] is True


def test_a_reply_with_no_mention_is_answered_in_striders_thread_with_its_session(
    mock_fn, mock_event, mock_context, slack, agent, thread, caplog
):
    event = thread_reply(mock_event)
    data = queued(event)

    mock_fn.handler(event, mock_context)

    assert thread.call_args.args[1:] == (CHANNEL, data['threadTs'], data['ts'], BOT)
    assert slack.steps == ['member?', 'eyes on', 'post', 'eyes off']
    assert slack.done[1] == ('eyes on', CHANNEL, data['ts'])
    assert slack.done[2] == ('post', CHANNEL, data['threadTs'], REPLY)
    assert agent.asked[0]['session'] == 'slack-T0123ABCD-C0123ABCDEF-' + data['threadTs'].replace('.', '-')
    assert agent.asked[0]['prompt'] == f'and what about the {DISTINCTIVE_WORD}?'
    assert outcome(caplog) == ('answered', None)


def test_the_first_time_strider_answers_in_a_thread_it_is_given_the_earlier_messages(
    mock_fn, mock_event, mock_context, agent, thread, caplog
):
    thread.return_value = ThreadRead(
        mentioned=True, answered_before=False,
        earlier=[('<@U1>', 'we deploy on Fridays'), ('<@U2>', 'except in December')],
    )

    mock_fn.handler(thread_reply(mock_event, text=f'<@{BOT}> when do we deploy?'), mock_context)

    assert agent.asked[0]['prompt'] == (
        'Earlier messages in this Slack thread, oldest first:\n'
        '<@U1>: we deploy on Fridays\n'
        '<@U2>: except in December\n'
        '\n'
        'Message to answer:\n'
        'when do we deploy?'
    )
    record = last_record(caplog)
    assert (record['contextMessages'], record['contextDropped']) == (2, 0)


def test_once_strider_has_answered_in_a_thread_the_message_is_sent_alone(mock_fn, mock_event, mock_context, agent, thread):
    thread.return_value = ThreadRead(mentioned=True, answered_before=True, earlier=[('<@U1>', 'earlier')])

    mock_fn.handler(thread_reply(mock_event, text='and in December?'), mock_context)

    assert agent.asked[0]['prompt'] == 'and in December?'


def test_earlier_messages_that_do_not_fit_are_left_out_oldest_first(
    mock_fn, mock_event, mock_context, agent, thread, monkeypatch, caplog
):
    monkeypatch.setenv('MAX_PROMPT_CHARS', '200')
    thread.return_value = ThreadRead(
        mentioned=True, answered_before=False,
        earlier=[('<@U1>', 'a' * 150), ('<@U2>', 'b' * 150), ('<@U3>', 'the newest')],
    )

    mock_fn.handler(thread_reply(mock_event, text=f'<@{BOT}> well?'), mock_context)

    prompt = agent.asked[0]['prompt']
    assert 'the newest' in prompt and 'a' * 150 not in prompt and 'b' * 150 not in prompt
    assert prompt.startswith('Some earlier messages were left out.')
    record = last_record(caplog)
    assert (record['contextMessages'], record['contextDropped']) == (1, 2)


def test_a_mention_is_recognised_from_the_text_whatever_kind_of_event_arrived(
    mock_fn, mock_event, mock_context, slack, thread, caplog
):
    # The message twin of a mention can reach the queue first, as an ordinary message.
    thread.side_effect = SlackUnavailable('ratelimited')
    event = thread_reply(mock_event, eventType='message', text=f'<@{BOT}> are you there?')

    mock_fn.handler(event, mock_context)

    assert slack.posts == [text.APOLOGY]


def test_a_mention_in_a_thread_older_than_the_agents_memory_gets_the_start_again_sentence(
    mock_fn, mock_event, mock_context, slack, agent, thread, caplog
):
    event = thread_reply(mock_event, threadTs=ts_ago(8 * SECONDS_IN_A_DAY), eventType='app_mention',
                         channelType='unknown', text=f'<@{BOT}> where were we?')
    data = queued(event)

    mock_fn.handler(event, mock_context)

    thread.assert_not_called()
    assert agent.asked == []
    assert slack.steps == ['member?', 'eyes on', 'post', 'eyes off']
    assert slack.done[2] == ('post', CHANNEL, data['threadTs'], text.START_AGAIN)
    assert outcome(caplog) == ('declined', 'thread_expired')


def test_a_reply_with_no_mention_in_an_old_thread_gets_nothing(mock_fn, mock_event, mock_context, slack, thread, caplog):
    mock_fn.handler(thread_reply(mock_event, threadTs=ts_ago(8 * SECONDS_IN_A_DAY)), mock_context)

    assert slack.done == []
    thread.assert_not_called()
    assert outcome(caplog) == ('declined', 'thread_expired')


def test_a_guest_who_mentions_strider_in_an_old_thread_gets_nothing(mock_fn, mock_event, mock_context, slack, caplog):
    slack.member = False
    event = thread_reply(mock_event, threadTs=ts_ago(8 * SECONDS_IN_A_DAY), text=f'<@{BOT}> hello')

    mock_fn.handler(event, mock_context)

    assert slack.steps == ['member?']
    assert outcome(caplog) == ('declined', 'not_member')


def test_a_thread_that_cannot_be_read_and_a_message_with_no_mention_gets_nothing(
    mock_fn, mock_event, mock_context, slack, agent, thread, caplog
):
    thread.side_effect = SlackUnavailable('ratelimited')

    result = mock_fn.handler(thread_reply(mock_event), mock_context)

    assert result == {'batchItemFailures': []}
    assert slack.done == []
    assert agent.asked == []
    assert outcome(caplog) == ('failed', 'thread_unreadable')


def test_a_thread_that_cannot_be_read_gets_the_apology_when_a_member_mentioned_strider(
    mock_fn, mock_event, mock_context, slack, agent, thread, caplog
):
    thread.side_effect = SlackUnavailable('ratelimited')

    mock_fn.handler(thread_reply(mock_event, text=f'<@{BOT}> what do you think?'), mock_context)

    assert slack.steps == ['member?', 'eyes on', 'post', 'eyes off']
    assert slack.posts == [text.APOLOGY]
    assert agent.asked == []
    assert outcome(caplog) == ('failed', 'thread_unreadable')


def test_a_thread_that_cannot_be_read_gets_nothing_when_a_guest_mentioned_strider(
    mock_fn, mock_event, mock_context, slack, thread, caplog
):
    thread.side_effect = SlackUnavailable('ratelimited')
    slack.member = False

    mock_fn.handler(thread_reply(mock_event, text=f'<@{BOT}> what do you think?'), mock_context)

    assert slack.posts == []
    assert outcome(caplog) == ('declined', 'not_member')


def test_two_threads_never_share_a_session(mock_fn, mock_event, mock_context, agent):
    mock_fn.handler(thread_reply(mock_event, threadTs=ts_ago(600)), mock_context)
    mock_fn.handler(thread_reply(mock_event, threadTs=ts_ago(300)), mock_context)

    first, second = agent.asked
    assert first['session'] != second['session']


def test_two_people_in_one_thread_share_a_session(mock_fn, mock_event, mock_context, agent):
    thread_ts = ts_ago(600)
    mock_fn.handler(thread_reply(mock_event, threadTs=thread_ts, user='U0FIRST'), mock_context)
    mock_fn.handler(thread_reply(mock_event, threadTs=thread_ts, user='U0SECOND'), mock_context)

    first, second = agent.asked
    assert first['session'] == second['session']
    assert (first['user'], second['user']) == ('U0FIRST', 'U0SECOND')


### A direct message (User Story 5)
def test_a_direct_message_is_answered_without_a_mention_and_without_reading_the_thread(
    mock_fn, mock_event, mock_context, slack, agent, thread, caplog
):
    event = direct_message(mock_event)
    data = queued(event)

    mock_fn.handler(event, mock_context)

    thread.assert_not_called()
    assert slack.done[2] == ('post', 'D0123ABCDEF', data['ts'], REPLY)
    assert agent.asked[0]['prompt'] == f'tell me about the {DISTINCTIVE_WORD}'
    assert outcome(caplog) == ('answered', None)


def test_a_reply_in_a_direct_message_thread_continues_that_threads_session(mock_fn, mock_event, mock_context, agent, thread):
    thread_ts = ts_ago(600)
    mock_fn.handler(direct_message(mock_event, ts=thread_ts, threadTs=thread_ts), mock_context)
    mock_fn.handler(direct_message(mock_event, threadTs=thread_ts, isReply=True), mock_context)

    first, second = agent.asked
    assert first['session'] == second['session']
    thread.assert_not_called()


def test_a_second_top_level_direct_message_starts_a_new_session(mock_fn, mock_event, mock_context, agent):
    mock_fn.handler(direct_message(mock_event, ts=ts_ago(60), threadTs=ts_ago(60)), mock_context)
    mock_fn.handler(direct_message(mock_event), mock_context)

    first, second = agent.asked
    assert first['session'] != second['session']


def test_a_guest_who_sends_a_direct_message_gets_nothing(mock_fn, mock_event, mock_context, slack, agent, caplog):
    slack.member = False

    mock_fn.handler(direct_message(mock_event), mock_context)

    assert slack.steps == ['member?']
    assert agent.asked == []
    assert outcome(caplog) == ('declined', 'not_member')


def test_a_reply_in_an_old_direct_message_thread_gets_the_start_again_sentence(
    mock_fn, mock_event, mock_context, slack, agent, caplog
):
    event = direct_message(mock_event, threadTs=ts_ago(8 * SECONDS_IN_A_DAY), isReply=True)

    mock_fn.handler(event, mock_context)

    assert slack.posts == [text.START_AGAIN]
    assert agent.asked == []
    assert outcome(caplog) == ('declined', 'thread_expired')


### When something goes wrong (User Story 6)
def test_an_agent_that_fails_once_and_then_answers_gives_the_reply_and_no_apology(
    mock_fn, mock_event, mock_context, slack, agent, caplog
):
    agent.replies = [AgentFailed('TimeoutError'), AgentReply('answer', REPLY, 'r-2')]

    mock_fn.handler(mention(mock_event), mock_context)

    assert len(agent.asked) == 2
    assert slack.posts == [REPLY]
    assert last_record(caplog)['attempts'] == 2
    assert last_record(caplog)['agentRequestId'] == 'r-2'
    mock_fn.time.sleep.assert_called_once_with(2)


def test_an_agent_that_fails_twice_gives_one_apology_and_no_third_try(
    mock_fn, mock_event, mock_context, slack, agent, caplog
):
    agent.replies = [AgentFailed('RuntimeError')]

    result = mock_fn.handler(mention(mock_event), mock_context)

    # The worker dealt with it, so the message does not go to the held-back queue.
    assert result == {'batchItemFailures': []}
    assert len(agent.asked) == 2
    assert slack.steps == ['member?', 'eyes on', 'post', 'eyes off']
    assert slack.posts == [text.APOLOGY]
    assert 'RuntimeError' not in slack.posts[0]
    assert outcome(caplog) == ('failed', 'agent_failed')
    assert last_record(caplog)['attempts'] == 2


def test_a_mention_with_no_other_text_is_asked_what_it_wants(mock_fn, mock_event, mock_context, slack, agent, caplog):
    mock_fn.handler(mention(mock_event, text=f'<@{BOT}>  '), mock_context)

    assert slack.steps == ['member?', 'eyes on', 'post', 'eyes off']
    assert slack.posts == [text.NOTHING_ASKED]
    assert agent.asked == []
    assert outcome(caplog) == ('declined', 'nothing_asked')


def test_an_empty_direct_message_is_asked_what_it_wants(mock_fn, mock_event, mock_context, slack, agent):
    mock_fn.handler(direct_message(mock_event, text=''), mock_context)

    assert slack.posts == [text.NOTHING_ASKED]
    assert agent.asked == []


def test_a_file_on_its_own_in_striders_thread_gets_nothing_posted(mock_fn, mock_event, mock_context, slack, agent, caplog):
    mock_fn.handler(thread_reply(mock_event, text=''), mock_context)

    assert slack.posts == []
    assert slack.steps == ['member?', 'eyes on', 'eyes off']
    assert agent.asked == []
    assert outcome(caplog) == ('declined', 'nothing_asked')


def test_a_message_over_the_agents_limit_is_told_it_is_too_long(
    mock_fn, mock_event, mock_context, slack, agent, monkeypatch, caplog
):
    monkeypatch.setenv('MAX_PROMPT_CHARS', '50')

    mock_fn.handler(mention(mock_event, text=f'<@{BOT}> ' + 'x' * 51), mock_context)

    assert slack.posts == [text.TOO_LONG]
    assert agent.asked == []
    assert outcome(caplog) == ('declined', 'too_long')


def test_a_message_the_agent_rejects_is_told_it_is_too_long_and_is_not_tried_again(
    mock_fn, mock_event, mock_context, slack, agent, caplog
):
    agent.replies = [AgentReply('input_rejection', 'The prompt is too long. The limit is 4000 characters.', 'r-3')]

    mock_fn.handler(mention(mock_event), mock_context)

    assert len(agent.asked) == 1
    assert slack.posts == [text.TOO_LONG]
    assert outcome(caplog) == ('declined', 'too_long')


def test_a_long_reply_whose_second_part_cannot_be_posted_is_announced_as_incomplete(
    mock_fn, mock_event, mock_context, slack, agent, caplog
):
    agent.replies = [AgentReply('answer', 'x' * 25000, 'r-1')]
    slack.posts_that_fail = {2}

    mock_fn.handler(mention(mock_event), mock_context)

    assert len(slack.posts) == 2
    assert slack.posts[0].endswith('(part 1 of 3)')
    assert slack.posts[1] == text.REPLY_INCOMPLETE
    assert slack.steps[-1] == 'eyes off'
    assert outcome(caplog) == ('failed', 'reply_not_posted')
    assert last_record(caplog)['replyParts'] == 1


def test_a_reply_that_cannot_be_posted_at_all_gets_the_apology(mock_fn, mock_event, mock_context, slack, caplog):
    slack.posts_that_fail = {REPLY}

    mock_fn.handler(mention(mock_event), mock_context)

    assert slack.posts == [text.APOLOGY]
    assert outcome(caplog) == ('failed', 'reply_not_posted')


def test_not_knowing_striders_own_identity_gets_nothing(mock_fn, mock_event, mock_context, slack, agent, caplog):
    slack.bot = SlackUnavailable('invalid_auth')

    result = mock_fn.handler(mention(mock_event), mock_context)

    assert result == {'batchItemFailures': []}
    assert slack.done == []
    assert agent.asked == []
    assert outcome(caplog) == ('failed', 'identity_unknown')


@pytest.mark.parametrize('replies', [
    [AgentReply('answer', REPLY, 'r-1')],
    [AgentFailed('x'), AgentReply('answer', REPLY, 'r-1')],
    [AgentFailed('x')],
    [AgentReply('input_rejection', 'too long', 'r-1')],
])
def test_a_person_never_gets_both_a_reply_and_the_apology(mock_fn, mock_event, mock_context, slack, agent, replies):
    agent.replies = replies

    mock_fn.handler(mention(mock_event), mock_context)

    assert len(slack.posts) == 1


def test_an_error_nobody_expected_reports_the_message_unfinished_and_still_removes_the_eyes(
    mock_fn, mock_event, mock_context, slack, agent, caplog, capsys
):
    agent.replies = [ValueError(f'something about the {DISTINCTIVE_WORD}')]
    event = mention(mock_event)

    result = mock_fn.handler(event, mock_context)

    # Reported, so the queue moves the message to the held-back queue for cleanup.
    assert result == {'batchItemFailures': [{'itemIdentifier': event['Records'][0]['messageId']}]}
    assert slack.steps == ['member?', 'eyes on', 'eyes off']
    record = last_record(caplog)
    assert (record['outcome'], record['errorType']) == ('unfinished', 'ValueError')
    assert DISTINCTIVE_WORD not in everything_logged(caplog, capsys)


def test_once_one_message_of_a_batch_fails_the_rest_are_reported_too(mock_fn, mock_event, mock_context, slack, agent):
    agent.replies = [ValueError('unexpected')]
    event = mention(mock_event)
    second = copy.deepcopy(event['Records'][0])
    second['messageId'] = 'second-message'
    event['Records'].append(second)

    result = mock_fn.handler(event, mock_context)

    assert [failure['itemIdentifier'] for failure in result['batchItemFailures']] == [
        event['Records'][0]['messageId'], 'second-message'
    ]
    assert len(agent.asked) == 1
