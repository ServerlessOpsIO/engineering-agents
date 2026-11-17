'''Tests for what reading a Slack thread tells the receiving service.'''

import pytest

from common.slack import text
from common.slack.errors import SlackUnavailable
from common.slack.thread import read_thread, since_message, thread_expired

BOT = 'U0STRIDER'
CHANNEL = 'C0123ABCDEF'
THREAD = '1731790000.000100'
DAY = 86400


def said(ts, user, words, **more):
    message = {'ts': ts, 'user': user, 'text': words, 'thread_ts': THREAD}
    message.update(more)
    return message


class FakeClient:
    '''Stands in for slack_sdk.WebClient.conversations_replies, one page per call.'''

    def __init__(self, *pages, error=None):
        self.pages = list(pages)
        self.error = error
        self.calls = []

    def conversations_history(self, **arguments):
        self.history_calls = getattr(self, 'history_calls', 0) + 1
        return self.conversations_replies(**arguments)

    def conversations_replies(self, **arguments):
        self.calls.append(arguments)
        if self.error:
            raise self.error
        page = self.pages[len(self.calls) - 1]
        more = len(self.calls) < len(self.pages)
        return {
            'ok': True,
            'messages': page,
            'has_more': more,
            'response_metadata': {'next_cursor': f'cursor-{len(self.calls)}' if more else ''},
        }


### How old a thread is
def test_a_thread_is_expired_only_after_the_memory_period():
    now = 1731790000 + 7 * DAY
    assert not thread_expired('1731790000.000100', 7, now)
    assert thread_expired('1731790000.000100', 7, now + 1)
    assert not thread_expired('1731790000.000100', 30, now + 1)


### Reading a thread up to a message
def test_the_thread_is_read_up_to_and_including_the_message():
    client = FakeClient([said(THREAD, 'U1', 'we deploy on Fridays'),
                         said('1731790010.000200', 'U2', f'<@{BOT}> when do we deploy?')])

    read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    [call] = client.calls
    assert call['channel'] == CHANNEL
    assert call['ts'] == THREAD
    assert call['latest'] == '1731790010.000200'
    assert call['inclusive'] is True
    assert call['limit'] == 200


def test_a_mention_in_the_message_makes_the_thread_striders():
    client = FakeClient([said(THREAD, 'U1', 'we deploy on Fridays'),
                         said('1731790010.000200', 'U2', f'<@{BOT}> when do we deploy?')])

    thread = read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    assert thread.mentioned is True
    assert thread.answered_before is False
    assert thread.earlier == [('<@U1>', 'we deploy on Fridays')]


def test_an_earlier_mention_by_anyone_makes_the_thread_striders():
    client = FakeClient([said(THREAD, 'U0GUEST', f'<@{BOT}> hello'),
                         said('1731790010.000200', 'U2', 'and another thing')])

    assert read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT).mentioned is True


def test_a_thread_with_no_mention_is_not_striders():
    client = FakeClient([said(THREAD, 'U1', 'we deploy on Fridays'),
                         said('1731790010.000200', 'U2', 'do we?')])

    thread = read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    assert thread.mentioned is False


def test_a_reply_from_strider_means_it_has_answered_before():
    client = FakeClient([said(THREAD, 'U1', f'<@{BOT}> when do we deploy?'),
                         said('1731790005.000150', BOT, 'On Fridays.', bot_id='B0STRIDER'),
                         said('1731790010.000200', 'U1', 'thanks, and in December?')])

    thread = read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    assert thread.answered_before is True
    assert thread.earlier[1] == ('STRIDEr', 'On Fridays.')


@pytest.mark.parametrize('sentence', sorted(text.FIXED_SENTENCES))
def test_a_fixed_sentence_from_strider_is_not_an_answer(sentence):
    client = FakeClient([said(THREAD, 'U1', f'<@{BOT}> when do we deploy?'),
                         said('1731790005.000150', BOT, sentence),
                         said('1731790010.000200', 'U1', 'hello?')])

    assert read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT).answered_before is False


def test_part_of_a_reply_counts_as_an_answer_because_the_agent_remembers_it():
    client = FakeClient([said(THREAD, 'U1', f'<@{BOT}> explain'),
                         said('1731790005.000150', BOT, 'A long reply\n\n(part 1 of 3)'),
                         said('1731790010.000200', 'U1', 'go on')])

    assert read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT).answered_before is True


def test_earlier_messages_are_in_order_and_leave_out_those_with_no_text():
    client = FakeClient([said('1731790008.000180', None, 'a notice from an app', bot_id='B0OTHER'),
                         said(THREAD, 'U1', 'first'),
                         said('1731790004.000140', 'U2', '', files=[{'id': 'F1'}]),
                         said('1731790010.000200', 'U3', f'<@{BOT}> last')])

    thread = read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    assert thread.earlier == [('<@U1>', 'first'), ('An app', 'a notice from an app')]


def test_messages_after_the_one_being_answered_are_not_used():
    client = FakeClient([said(THREAD, 'U1', 'first'),
                         said('1731790010.000200', 'U2', 'the message'),
                         said('1731790020.000300', 'U3', f'<@{BOT}> later')])

    thread = read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    assert thread.mentioned is False
    assert thread.earlier == [('<@U1>', 'first')]


def test_a_long_thread_is_read_page_by_page():
    client = FakeClient([said(THREAD, 'U1', 'first')],
                        [said('1731790005.000150', 'U2', f'<@{BOT}> second')],
                        [said('1731790010.000200', 'U3', 'third')])

    thread = read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    assert [call['cursor'] for call in client.calls] == [None, 'cursor-1', 'cursor-2']
    assert thread.mentioned is True
    assert len(thread.earlier) == 2


def test_a_thread_slack_will_not_show_is_reported_without_the_cause_attached():
    client = FakeClient(error=RuntimeError('ratelimited while reading: a distinctive message'))

    with pytest.raises(SlackUnavailable) as raised:
        read_thread(client, CHANNEL, THREAD, '1731790010.000200', BOT)

    assert 'distinctive' not in str(raised.value)
    assert raised.value.__cause__ is None


### Reading a thread from a message onward
MESSAGE_TS = '1731790010.000200'


def eyes(*users):
    return [{'name': 'eyes', 'users': list(users), 'count': len(users)}]


def test_the_thread_is_read_from_the_message_onward():
    client = FakeClient([said(MESSAGE_TS, 'U1', 'a question')])

    since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT)

    [call] = client.calls
    assert (call['ts'], call['oldest'], call['inclusive']) == (THREAD, MESSAGE_TS, True)


def test_eyes_from_strider_on_the_message_are_seen():
    client = FakeClient([said(THREAD, 'U1', 'the parent'),
                         said(MESSAGE_TS, 'U1', 'a question', reactions=eyes('U9', BOT))])

    since = since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT)

    assert (since.found, since.has_eyes, since.posted, since.incomplete) == (True, True, False, False)


def test_eyes_from_a_person_only_do_not_count():
    client = FakeClient([said(MESSAGE_TS, 'U1', 'a question', reactions=eyes('U9'))])
    assert since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT).has_eyes is False


def test_another_reaction_from_strider_does_not_count():
    client = FakeClient([said(MESSAGE_TS, 'U1', 'q', reactions=[{'name': 'thumbsup', 'users': [BOT]}])])
    assert since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT).has_eyes is False


def test_a_post_from_strider_after_the_message_is_seen():
    client = FakeClient([said(MESSAGE_TS, 'U1', 'a question', reactions=eyes(BOT)),
                         said('1731790015.000250', BOT, 'An answer.')])

    since = since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT)

    assert (since.posted, since.incomplete) == (True, False)


def test_a_post_from_someone_else_or_from_before_the_message_does_not_count():
    client = FakeClient([said(THREAD, BOT, 'An earlier answer.'),
                         said(MESSAGE_TS, 'U1', 'a question', reactions=eyes(BOT)),
                         said('1731790015.000250', 'U2', 'I think so too')])

    assert since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT).posted is False


def test_a_last_post_that_is_not_the_final_part_is_incomplete():
    client = FakeClient([said(MESSAGE_TS, 'U1', 'explain', reactions=eyes(BOT)),
                         said('1731790015.000250', BOT, 'start\n\n(part 1 of 3)'),
                         said('1731790016.000260', BOT, 'middle\n\n(part 2 of 3)')])

    since = since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT)

    assert (since.posted, since.incomplete) == (True, True)


def test_a_reply_whose_final_part_was_posted_is_complete():
    client = FakeClient([said(MESSAGE_TS, 'U1', 'explain', reactions=eyes(BOT)),
                         said('1731790015.000250', BOT, 'start\n\n(part 1 of 2)'),
                         said('1731790016.000260', BOT, 'end\n\n(part 2 of 2)')])

    assert since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT).incomplete is False


def test_a_message_that_has_been_deleted_is_not_found():
    client = FakeClient([said(THREAD, 'U1', 'the parent')])

    since = since_message(client, CHANNEL, THREAD, MESSAGE_TS, BOT)

    assert (since.found, since.has_eyes, since.posted) == (False, False, False)


### Reading a direct message from a message onward
def test_with_no_thread_the_conversation_itself_is_read():
    client = FakeClient([said('1731790015.000250', BOT, 'An answer.', thread_ts=None),
                         said(MESSAGE_TS, 'U1', 'a question', reactions=eyes(BOT), thread_ts=None)])

    since = since_message(client, 'D0123ABCDEF', None, MESSAGE_TS, BOT)

    assert client.history_calls == 1
    [call] = client.calls
    assert call['channel'] == 'D0123ABCDEF'
    assert (call['oldest'], call['inclusive']) == (MESSAGE_TS, True)
    assert 'ts' not in call
    assert (since.found, since.has_eyes, since.posted, since.incomplete) == (True, True, True, False)


def test_with_no_thread_and_nothing_posted_an_apology_is_still_owed():
    client = FakeClient([said(MESSAGE_TS, 'U1', 'a question', reactions=eyes(BOT), thread_ts=None)])

    since = since_message(client, 'D0123ABCDEF', None, MESSAGE_TS, BOT)

    assert (since.has_eyes, since.posted) == (True, False)
