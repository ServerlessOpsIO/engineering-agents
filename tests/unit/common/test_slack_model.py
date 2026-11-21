'''Tests for the records the Slack receiving service passes between its parts.'''

import pytest

from common.model.slack import QueuedMessage


def message(**changes) -> QueuedMessage:
    fields = {
        'teamId': 'T0123ABCD',
        'channel': 'C0123ABCDEF',
        'channelType': 'channel',
        'ts': '1731790042.222222',
        'threadTs': '1731790000.111111',
        'isReply': True,
        'user': 'U0123ABCD',
        'text': 'an invented question',
        'eventType': 'message',
        'eventId': 'Ev0123ABCD',
        'correlationId': '00000000-0000-0000-0000-000000000000',
        'receivedAt': '2026-11-16T12:00:00+00:00',
    }
    fields.update(changes)
    return QueuedMessage(**fields)


def test_a_message_survives_a_round_trip_through_json():
    original = message()
    assert QueuedMessage.from_json(original.to_json()) == original


def test_the_group_is_the_thread():
    assert message().message_group_id() == 'C0123ABCDEF:1731790000.111111'


def test_the_deduplication_id_is_the_message():
    assert message().deduplication_id() == 'C0123ABCDEF:1731790042.222222'


def test_the_session_is_built_from_the_thread_for_a_reply():
    assert message().session_id() == 'slack-T0123ABCD-C0123ABCDEF-1731790000-111111'


def test_a_top_level_message_is_its_own_thread():
    top_level = message(ts='1731790000.111111', isReply=False)
    assert top_level.session_id() == 'slack-T0123ABCD-C0123ABCDEF-1731790000-111111'


def test_every_message_in_a_thread_gets_the_same_session():
    first = message(ts='1731790001.000001')
    second = message(ts='1731790002.000002', user='U0999ZZZZ')
    assert first.session_id() == second.session_id()


def test_different_threads_get_different_sessions():
    assert message().session_id() != message(threadTs='1731790099.999999').session_id()


def test_the_same_thread_in_another_channel_is_another_session():
    assert message().session_id() != message(channel='C0999ZZZZZZ').session_id()


def test_the_session_has_no_character_agentcore_may_refuse():
    session_id = message().session_id()
    assert len(session_id) >= 33
    assert '.' not in session_id


def test_a_session_that_would_be_too_short_is_refused():
    with pytest.raises(ValueError):
        message(teamId='T1', channel='C1', threadTs='1.1').session_id()


def test_a_session_with_an_unsafe_character_is_refused():
    with pytest.raises(ValueError):
        message(channel='C0123/ABCDEF').session_id()


def test_a_direct_message_is_recognised_by_its_channel_type():
    assert message(channelType='im').is_direct_message()
    assert not message(channelType='unknown').is_direct_message()


### Direct messages
def dm(**changes) -> QueuedMessage:
    fields = {'channel': 'D0123ABCDEF', 'channelType': 'im', 'ts': '1731790042.222222',
              'threadTs': '1731790042.222222', 'isReply': False}
    fields.update(changes)
    return message(**fields)


def test_a_direct_message_is_one_session_whatever_the_message_or_thread():
    first = dm()
    later = dm(ts='1731799999.000001', threadTs='1731799999.000001')
    in_a_thread = dm(ts='1731790050.333333', threadTs='1731790042.222222', isReply=True)
    assert first.session_id() == 'slack-T0123ABCD-D0123ABCDEF-direct-message'
    assert later.session_id() == first.session_id()
    assert in_a_thread.session_id() == first.session_id()
    assert len(first.session_id()) >= 33


def test_two_direct_message_conversations_are_two_sessions():
    assert dm().session_id() != dm(channel='D0999ZZZZZZ').session_id()


def test_a_direct_message_is_one_group_so_it_is_answered_in_order():
    in_a_thread = dm(ts='1731790050.333333', threadTs='1731790042.222222', isReply=True)
    assert dm().message_group_id() == 'D0123ABCDEF'
    assert in_a_thread.message_group_id() == 'D0123ABCDEF'


def test_a_reply_to_a_direct_message_goes_outside_any_thread():
    assert dm().reply_thread_ts() is None


def test_a_reply_to_a_thread_in_a_direct_message_goes_in_that_thread():
    in_a_thread = dm(ts='1731790050.333333', threadTs='1731790042.222222', isReply=True)
    assert in_a_thread.reply_thread_ts() == '1731790042.222222'


def test_a_reply_in_a_channel_always_goes_in_a_thread():
    top_level = message(ts='1731790000.111111', isReply=False)
    assert top_level.reply_thread_ts() == '1731790000.111111'
    assert message().reply_thread_ts() == '1731790000.111111'
    assert message(channelType='unknown').reply_thread_ts() == '1731790000.111111'


def test_spec_008_adds_an_outcome_and_a_reason():
    from common.model import slack as model
    assert model.OUTCOME_NO_REPLY == 'no_reply'
    assert model.REASON_DOCUMENT_NOT_POSTED == 'document_not_posted'
