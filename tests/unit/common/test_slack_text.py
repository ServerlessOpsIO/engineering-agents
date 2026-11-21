'''Tests for what STRIDEr reads from a Slack message and writes back.'''

import re

import pytest

from common.slack import text

BOT = 'U0STRIDER'
LABEL = re.compile(r'\n\n\(part \d+ of \d+\)$')


### The fixed sentences
def test_the_fixed_sentences_are_the_agreed_wording():
    assert text.APOLOGY == "Sorry, I couldn't answer that. Please try again later."
    assert text.TOO_LONG == (
        'That message is too long for me to read. Please shorten it and try again.'
    )
    assert text.NOTHING_ASKED == 'What would you like help with?'
    assert text.START_AGAIN == (
        'I no longer remember this conversation. '
        'Please send me a new message outside this thread to start again.'
    )
    assert text.REPLY_INCOMPLETE == "I couldn't post my whole reply. Please ask again."
    assert text.DOCUMENT_NOT_POSTED == "I couldn't post the document. Please ask me for it again."
    assert len(text.FIXED_SENTENCES) == 6


### Mentions
@pytest.mark.parametrize('message', [
    f'<@{BOT}> what is a trust boundary?',
    f'what is a trust boundary <@{BOT}|strider>?',
])
def test_both_forms_of_a_mention_are_recognised(message):
    assert text.mentions(message, BOT)


def test_a_mention_of_someone_else_is_not_a_mention():
    assert not text.mentions('<@U0SOMEONE> hello', BOT)
    assert not text.mentions('', BOT)
    assert not text.mentions(None, BOT)


def test_the_mention_is_removed_and_nothing_else_changes():
    message = f'<@{BOT}> ask <@U0SOMEONE> about *this* & <https://example.com|that>'
    assert text.strip_mention(message, BOT) == (
        'ask <@U0SOMEONE> about *this* & <https://example.com|that>'
    )


def test_the_older_form_of_mention_is_removed_too():
    assert text.strip_mention(f'hello <@{BOT}|strider>', BOT) == 'hello'


def test_a_message_that_is_only_a_mention_leaves_nothing():
    assert text.strip_mention(f'  <@{BOT}>  ', BOT) == ''


### The prompt
def test_a_prompt_with_no_earlier_messages_is_the_message():
    assert text.build_prompt('what next?', [], 100) == ('what next?', 0)


def test_earlier_messages_come_first_in_order_with_their_writers():
    earlier = [('<@U1>', 'we deploy on Fridays'), ('<@U2>', 'except in December')]
    prompt, dropped = text.build_prompt('when do we deploy?', earlier, 1000)
    assert dropped == 0
    assert prompt == (
        'Earlier messages in this Slack thread, oldest first:\n'
        '<@U1>: we deploy on Fridays\n'
        '<@U2>: except in December\n'
        '\n'
        'Message to answer:\n'
        'when do we deploy?'
    )


def test_the_oldest_earlier_messages_are_left_out_first():
    earlier = [('<@U1>', 'a' * 100), ('<@U2>', 'b' * 100), ('<@U3>', 'c' * 20)]
    prompt, dropped = text.build_prompt('the question', earlier, 150)
    assert dropped == 2
    assert 'a' * 100 not in prompt and 'b' * 100 not in prompt
    assert 'c' * 20 in prompt
    assert prompt.startswith('Some earlier messages were left out. The rest, oldest first:')
    assert prompt.endswith('Message to answer:\nthe question')
    assert len(prompt) <= 150


def test_when_no_earlier_message_fits_the_agent_is_still_told():
    earlier = [('<@U1>', 'a' * 500)]
    prompt, dropped = text.build_prompt('the question', earlier, 200)
    assert dropped == 1
    assert 'were left out' in prompt
    assert prompt.endswith('the question')


def test_when_nothing_but_the_message_fits_the_message_is_sent_alone():
    earlier = [('<@U1>', 'a' * 500)]
    assert text.build_prompt('q' * 95, earlier, 100) == ('q' * 95, 1)


def test_the_message_is_never_shortened():
    with pytest.raises(text.TooLong):
        text.build_prompt('q' * 101, [], 100)
    with pytest.raises(text.TooLong):
        text.build_prompt('q' * 101, [('<@U1>', 'earlier')], 100)


def test_a_message_exactly_at_the_limit_is_accepted():
    assert text.build_prompt('q' * 100, [], 100) == ('q' * 100, 0)


### Splitting a reply
def test_a_short_reply_is_one_part_with_no_label():
    assert text.split_reply('a short reply') == ['a short reply']


def test_a_reply_exactly_at_the_limit_is_one_part():
    reply = 'x' * 11000
    assert text.split_reply(reply) == [reply]


def test_a_long_reply_is_split_into_labelled_parts_with_nothing_lost():
    paragraphs = [f'Paragraph {number}. ' + 'word ' * 150 for number in range(33)]
    reply = '\n\n'.join(paragraphs)
    assert len(reply) > 22000

    parts = text.split_reply(reply)

    assert len(parts) == 3
    for number, part in enumerate(parts, 1):
        assert len(part) <= 11000
        assert part.endswith(f'(part {number} of 3)')
    assert ''.join(LABEL.sub('', part) for part in parts) == reply


def test_a_long_reply_is_split_at_paragraph_breaks_when_there_are_any():
    reply = ('a' * 6000) + '\n\n' + ('b' * 6000)
    first, second = text.split_reply(reply)
    assert LABEL.sub('', first) == ('a' * 6000) + '\n\n'
    assert LABEL.sub('', second) == 'b' * 6000


def test_a_long_reply_with_no_paragraphs_is_split_at_a_line_break():
    reply = ('a' * 6000) + '\n' + ('b' * 6000)
    first, second = text.split_reply(reply)
    assert LABEL.sub('', first) == ('a' * 6000) + '\n'
    assert LABEL.sub('', second) == 'b' * 6000


def test_a_long_reply_with_no_breaks_at_all_is_still_split_with_nothing_lost():
    reply = 'x' * 25000
    parts = text.split_reply(reply)
    assert len(parts) == 3
    assert all(len(part) <= 11000 for part in parts)
    assert ''.join(LABEL.sub('', part) for part in parts) == reply


### Recognising an unfinished reply
def test_a_part_that_is_not_the_last_is_incomplete():
    first, second, third = text.split_reply('x' * 25000)
    assert text.incomplete_part(first)
    assert text.incomplete_part(second)
    assert not text.incomplete_part(third)


def test_an_unlabelled_reply_is_not_incomplete():
    assert not text.incomplete_part('a short reply')
    assert not text.incomplete_part(text.APOLOGY)
    assert not text.incomplete_part('')
    assert not text.incomplete_part(None)


### People are named (spec 008: FR-030)
def _names():
    looked_up = []

    def name_of(user):
        looked_up.append(user)
        return {'U1': 'Uma One', 'W2': 'Wim Two'}.get(user, 'Robin Example')
    return name_of, looked_up


def test_a_mention_of_a_person_becomes_their_name():
    name_of, _ = _names()
    assert text.name_people('ask <@U1> and <@W2|wim> and <@U3>', name_of, {}) == (
        'ask Uma One and Wim Two and Robin Example'
    )


def test_a_name_already_known_is_not_looked_up_again():
    name_of, looked_up = _names()
    known = {'U0STRIDER': 'STRIDEr'}
    assert text.name_people('<@U0STRIDER> <@U1> <@U1>', name_of, {}, known) == 'STRIDEr Uma One Uma One'
    assert looked_up == ['U1']


def test_only_ten_different_people_are_named():
    name_of, looked_up = _names()
    said = ' '.join(f'<@U{n:03d}>' for n in range(12))
    result = text.name_people(said, name_of, {})
    assert result.count('Robin Example') == 10 and result.count('someone') == 2
    assert len(looked_up) == 10


def test_channels_links_and_text_without_mentions_are_left_alone():
    name_of, looked_up = _names()
    said = 'see <#C123|general> and <https://example.com|this> & that'
    assert text.name_people(said, name_of, {}) == said
    assert text.name_people('', name_of, {}) == '' and text.name_people(None, name_of, {}) == ''
    assert looked_up == []
