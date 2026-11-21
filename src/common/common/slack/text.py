'''What STRIDEr reads from a Slack message and what it writes back.

Nothing in this module logs. Every function takes and returns message text,
which must never reach a log.
'''

import re
from typing import Callable, List, Sequence, Tuple

# The only words STRIDEr posts that the agent does not write.
APOLOGY = "Sorry, I couldn't answer that. Please try again later."
TOO_LONG = 'That message is too long for me to read. Please shorten it and try again.'
NOTHING_ASKED = 'What would you like help with?'
START_AGAIN = (
    'I no longer remember this conversation. '
    'Please send me a new message outside this thread to start again.'
)
REPLY_INCOMPLETE = "I couldn't post my whole reply. Please ask again."
DOCUMENT_NOT_POSTED = "I couldn't post the document. Please ask me for it again."

FIXED_SENTENCES = frozenset(
    {APOLOGY, TOO_LONG, NOTHING_ASKED, START_AGAIN, REPLY_INCOMPLETE, DOCUMENT_NOT_POSTED}
)

# How many different people's names are looked up for one message.
MAX_PEOPLE_NAMED = 10
SOMEONE = 'someone'
# A mention of a person: <@U123>, <@W123>, either with |label.
_PERSON = re.compile(r'<@([UW][A-Z0-9]+)(?:\|[^>]*)?>')

# Slack accepts 12,000 characters of Markdown in one message.
REPLY_PART_CHARS = 11000
# Room kept in each part for its label.
_LABEL_ROOM = 40

CONTEXT_HEADING = 'Earlier messages in this Slack thread, oldest first:'
CONTEXT_HEADING_DROPPED = 'Some earlier messages were left out. The rest, oldest first:'
CONTEXT_ALL_DROPPED = 'Earlier messages in this Slack thread were left out because they were too long.'
MESSAGE_HEADING = 'Message to answer:'

_PART_LABEL = re.compile(r'\(part (\d+) of (\d+)\)\s*$')


class TooLong(Exception):
    '''The message alone is longer than the agent accepts.'''


def _mention_pattern(bot_user_id: str) -> 're.Pattern':
    # Slack writes a mention as <@U123> and, in an older form, <@U123|name>.
    return re.compile(r'<@' + re.escape(bot_user_id) + r'(\|[^>]*)?>')


def mentions(text: str, bot_user_id: str) -> bool:
    '''Say whether the text mentions the user.'''
    return bool(_mention_pattern(bot_user_id).search(text or ''))


def strip_mention(text: str, bot_user_id: str) -> str:
    '''Return the text with mentions of the user removed and nothing else changed.'''
    return _mention_pattern(bot_user_id).sub('', text or '').strip()


def name_people(text: str, name_of: Callable[[str], str], named: dict, known: dict = None) -> str:
    '''Return the text with each mention of a person replaced by their name.

    name_of gives the name for a user ID. known holds names already in hand,
    such as the writer's and STRIDEr's own, which cost no lookup. named
    remembers the names found, so that one message and its thread context share
    one limit: at most MAX_PEOPLE_NAMED different people are looked up, and any
    further ones become "someone". A message never shows a Slack identifier.
    '''
    known = known or {}

    def replace(match: 're.Match') -> str:
        user = match.group(1)
        if user in known:
            return known[user]
        if user not in named:
            if len(named) >= MAX_PEOPLE_NAMED:
                return SOMEONE
            named[user] = name_of(user)
        return named[user]
    return _PERSON.sub(replace, text or '')


def _with_context(heading: str, earlier: Sequence[Tuple[str, str]], text: str) -> str:
    lines = [heading]
    lines.extend(f'{writer}: {said}' for writer, said in earlier)
    return '\n'.join(lines) + f'\n\n{MESSAGE_HEADING}\n{text}'


def build_prompt(
    text: str, earlier: Sequence[Tuple[str, str]], max_chars: int
) -> Tuple[str, int]:
    '''Return the prompt for the agent and how many earlier messages were left out.

    earlier is the thread's earlier messages, oldest first, each a pair of who
    wrote it and what they wrote. The oldest are left out until the prompt fits
    in max_chars. The message being answered is never shortened.
    '''
    if len(text) > max_chars:
        raise TooLong()
    if not earlier:
        return text, 0

    kept = list(earlier)
    while kept:
        dropped = len(earlier) - len(kept)
        heading = CONTEXT_HEADING_DROPPED if dropped else CONTEXT_HEADING
        prompt = _with_context(heading, kept, text)
        if len(prompt) <= max_chars:
            return prompt, dropped
        kept.pop(0)

    # None of the earlier messages fit. Say so if there is room, so the agent
    # knows it is missing something.
    prompt = f'{CONTEXT_ALL_DROPPED}\n\n{MESSAGE_HEADING}\n{text}'
    if len(prompt) <= max_chars:
        return prompt, len(earlier)
    return text, len(earlier)


def _cut(text: str, limit: int) -> int:
    '''Return where to end a part: after a paragraph break, else a line break, else at the limit.'''
    window = text[:limit]
    for separator in ('\n\n', '\n'):
        position = window.rfind(separator)
        if position > 0:
            return position + len(separator)
    return limit


def split_reply(text: str, limit: int = REPLY_PART_CHARS) -> List[str]:
    '''Return the reply as one or more parts, none longer than limit.

    No text is lost: the parts, without their labels, join back to the reply.
    When there is more than one part each ends with "(part n of m)".
    '''
    if len(text) <= limit:
        return [text]

    body_limit = limit - _LABEL_ROOM
    bodies = []
    rest = text
    while len(rest) > body_limit:
        cut = _cut(rest, body_limit)
        bodies.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        bodies.append(rest)

    total = len(bodies)
    return [f'{body}\n\n(part {number} of {total})' for number, body in enumerate(bodies, 1)]


def incomplete_part(text: str) -> bool:
    '''Say whether the text is a labelled part of a reply that is not the final part.'''
    label = _PART_LABEL.search(text or '')
    return bool(label) and int(label.group(1)) < int(label.group(2))
