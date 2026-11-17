'''Test CleanUpSlackMessage'''

import json
import os
from types import ModuleType
from typing import Generator

import jsonschema
import pytest
from pytest_mock import MockerFixture

from common.slack import text
from common.slack.errors import SlackUnavailable
from common.slack.thread import SinceMessage

FN_NAME = 'CleanUpSlackMessage'
DATA_DIR = './data'
FUNC_DATA_DIR = os.path.join(DATA_DIR, 'handlers', FN_NAME)
EVENT = os.path.join(FUNC_DATA_DIR, 'event.json')
EVENT_SCHEMA = os.path.join(FUNC_DATA_DIR, 'event.schema.json')

BOT = 'U0STRIDER'
# A word that appears in the sample message and nowhere else.
DISTINCTIVE_WORD = 'heron'


def _load(path):
    with open(path) as f:
        return json.load(f)


class FakeSlack:
    '''Stands in for common.slack.api. Records what was done, in order.'''

    def __init__(self):
        self.done = []
        self.bot = BOT
        self.post_works = True
        self.eyes_removed = True

    def bot_user_id(self):
        if isinstance(self.bot, Exception):
            raise self.bot
        return self.bot

    def client(self):
        return 'a client'

    def remove_eyes(self, channel, ts):
        self.done.append(('eyes off', channel, ts))
        return self.eyes_removed

    def post(self, channel, thread_ts, markdown):
        self.done.append(('post' if self.post_works else 'post failed', channel, thread_ts, markdown))
        return self.post_works

    @property
    def steps(self):
        return [step[0] for step in self.done]


### Fixtures
@pytest.fixture()
def mock_context(lambda_function_context, function_name=FN_NAME):
    '''context object'''
    return lambda_function_context(function_name)


@pytest.fixture()
def mock_event() -> dict:
    '''An SQS event from the held-back queue'''
    return _load(EVENT)


@pytest.fixture()
def data(mock_event) -> dict:
    '''The queued message the event carries'''
    return json.loads(mock_event['Records'][0]['body'])


@pytest.fixture()
def slack() -> FakeSlack:
    return FakeSlack()


@pytest.fixture()
def since(mocker):
    '''What the thread shows from the message onward. Set .return_value or .side_effect.'''
    return mocker.patch(
        'src.handlers.CleanUpSlackMessage.function.since_message',
        return_value=SinceMessage(found=True, has_eyes=True, posted=False, incomplete=False),
    )


@pytest.fixture()
def mock_fn(slack, since, monkeypatch, mocker: MockerFixture) -> Generator[ModuleType, None, None]:
    '''The function module with Slack replaced'''
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'test')

    import src.handlers.CleanUpSlackMessage.function as fn

    mocker.patch('src.handlers.CleanUpSlackMessage.function.api', slack)
    yield fn


def last_record(caplog) -> dict:
    return vars(caplog.records[-1])


def outcome(caplog):
    record = last_record(caplog)
    return record['outcome'], record['reason']


### Data validation
def test_validate_event(mock_event):
    '''Test the sample event against the schema'''
    jsonschema.validate(mock_event, _load(EVENT_SCHEMA))


### The cases
def test_the_thread_is_read_from_the_unfinished_message_onward(mock_fn, mock_event, mock_context, since, data):
    mock_fn.handler(mock_event, mock_context)

    assert since.call_args.args[1:] == (data['channel'], data['threadTs'], data['ts'], BOT)


def test_a_message_without_the_eyes_was_never_started_so_nothing_is_done(
    mock_fn, mock_event, mock_context, slack, since, caplog
):
    since.return_value = SinceMessage(found=True, has_eyes=False)

    result = mock_fn.handler(mock_event, mock_context)

    assert result == {'batchItemFailures': []}
    assert slack.done == []
    assert outcome(caplog) == ('cleaned_up', 'not_started')


def test_a_message_that_has_been_deleted_gets_nothing(mock_fn, mock_event, mock_context, slack, since, caplog):
    since.return_value = SinceMessage(found=False)

    mock_fn.handler(mock_event, mock_context)

    assert slack.done == []
    assert outcome(caplog) == ('cleaned_up', 'not_started')


def test_eyes_and_nothing_posted_gets_the_apology_and_then_the_eyes_are_removed(
    mock_fn, mock_event, mock_context, slack, data, caplog
):
    result = mock_fn.handler(mock_event, mock_context)

    assert result == {'batchItemFailures': []}
    assert slack.done == [
        ('post', data['channel'], data['threadTs'], text.APOLOGY),
        ('eyes off', data['channel'], data['ts']),
    ]
    assert outcome(caplog) == ('cleaned_up', 'apologised')
    assert last_record(caplog)['reactionRemoved'] is True


def test_eyes_and_a_reply_already_posted_only_removes_the_eyes(mock_fn, mock_event, mock_context, slack, since, caplog):
    since.return_value = SinceMessage(found=True, has_eyes=True, posted=True, incomplete=False)

    mock_fn.handler(mock_event, mock_context)

    assert slack.steps == ['eyes off']
    assert outcome(caplog) == ('cleaned_up', 'already_answered')


def test_eyes_and_an_unfinished_reply_is_announced_as_incomplete(
    mock_fn, mock_event, mock_context, slack, since, data, caplog
):
    since.return_value = SinceMessage(found=True, has_eyes=True, posted=True, incomplete=True)

    mock_fn.handler(mock_event, mock_context)

    assert slack.done == [
        ('post', data['channel'], data['threadTs'], text.REPLY_INCOMPLETE),
        ('eyes off', data['channel'], data['ts']),
    ]
    assert outcome(caplog) == ('cleaned_up', 'reply_incomplete')


def test_running_twice_posts_one_apology(mock_fn, mock_event, mock_context, slack, since):
    mock_fn.handler(mock_event, mock_context)
    # The second run finds the apology the first posted, and the eyes gone.
    since.return_value = SinceMessage(found=True, has_eyes=False, posted=True)
    mock_fn.handler(mock_event, mock_context)

    assert [step for step in slack.steps if step == 'post'] == ['post']


def test_a_run_that_posted_but_could_not_remove_the_eyes_does_not_apologise_again(
    mock_fn, mock_event, mock_context, slack, since
):
    slack.eyes_removed = False
    mock_fn.handler(mock_event, mock_context)
    since.return_value = SinceMessage(found=True, has_eyes=True, posted=True)
    mock_fn.handler(mock_event, mock_context)

    assert [step for step in slack.steps if step == 'post'] == ['post']


### A direct message
def test_a_direct_message_is_cleaned_up_outside_any_thread(mock_fn, mock_event, mock_context, slack, since, data):
    data.update({'channel': 'D0123ABCDEF', 'channelType': 'im'})
    mock_event['Records'][0]['body'] = json.dumps(data)

    mock_fn.handler(mock_event, mock_context)

    # The direct message itself is read, not a thread, and the apology goes there.
    assert since.call_args.args[1:] == ('D0123ABCDEF', None, data['ts'], BOT)
    assert slack.done == [
        ('post', 'D0123ABCDEF', None, text.APOLOGY),
        ('eyes off', 'D0123ABCDEF', data['ts']),
    ]


def test_a_thread_in_a_direct_message_is_cleaned_up_in_that_thread(mock_fn, mock_event, mock_context, slack, since, data):
    data.update({'channel': 'D0123ABCDEF', 'channelType': 'im', 'threadTs': '1731780000.000001', 'isReply': True})
    mock_event['Records'][0]['body'] = json.dumps(data)

    mock_fn.handler(mock_event, mock_context)

    assert since.call_args.args[1:] == ('D0123ABCDEF', '1731780000.000001', data['ts'], BOT)
    assert slack.done[0] == ('post', 'D0123ABCDEF', '1731780000.000001', text.APOLOGY)


### When cleaning up fails
def test_an_apology_that_cannot_be_posted_leaves_the_eyes_and_is_tried_again(
    mock_fn, mock_event, mock_context, slack, caplog
):
    slack.post_works = False

    result = mock_fn.handler(mock_event, mock_context)

    assert result == {'batchItemFailures': [{'itemIdentifier': mock_event['Records'][0]['messageId']}]}
    assert slack.steps == ['post failed']
    assert last_record(caplog)['outcome'] == 'unfinished'


@pytest.mark.parametrize('broken', ['thread', 'identity'])
def test_slack_not_answering_means_the_message_is_offered_again(
    mock_fn, mock_event, mock_context, slack, since, caplog, broken
):
    if broken == 'thread':
        since.side_effect = SlackUnavailable('ratelimited')
    else:
        slack.bot = SlackUnavailable('invalid_auth')

    result = mock_fn.handler(mock_event, mock_context)

    assert result == {'batchItemFailures': [{'itemIdentifier': mock_event['Records'][0]['messageId']}]}
    assert slack.done == []
    record = last_record(caplog)
    assert (record['outcome'], record['errorType']) == ('unfinished', 'SlackUnavailable')


### Logging
def test_the_log_record_has_the_identifiers_and_no_text(mock_fn, mock_event, mock_context, data, caplog, capsys):
    mock_fn.handler(mock_event, mock_context)

    record = last_record(caplog)
    assert record['correlationId'] == data['correlationId']
    assert record['eventId'] == data['eventId']
    assert (record['channel'], record['threadTs'], record['ts']) == (data['channel'], data['threadTs'], data['ts'])
    assert record['user'] == data['user']
    assert isinstance(record['durationMs'], int)

    printed = capsys.readouterr()
    logged = '\n'.join([str(vars(entry)) for entry in caplog.records] + [printed.out, printed.err])
    assert DISTINCTIVE_WORD not in logged
    assert 'trust boundary' not in logged
