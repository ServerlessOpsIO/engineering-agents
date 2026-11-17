'''What reading a Slack thread tells the receiving service.

There is no database. Whether a thread is one STRIDEr takes part in, whether
STRIDEr has answered in it, and whether a message has been dealt with are all
read from Slack, where they are true.

Nothing in this module logs. It handles message text.
'''

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from common.slack.errors import SlackUnavailable
from common.slack.text import FIXED_SENTENCES, incomplete_part, mentions

EYES = 'eyes'
PAGE_SIZE = 200
SECONDS_IN_A_DAY = 86400
STRIDER = 'STRIDEr'


def thread_expired(thread_ts: str, days: int, now: float) -> bool:
    '''Say whether the thread began longer ago than the agent keeps memory.

    A thread's timestamp is the time its first message was sent.
    '''
    return now - float(thread_ts) > days * SECONDS_IN_A_DAY


@dataclass
class ThreadRead:
    '''What a thread shows, up to and including one message.'''
    mentioned: bool = False
    answered_before: bool = False
    earlier: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class SinceMessage:
    '''What a thread shows from one message onward.'''
    found: bool = False
    has_eyes: bool = False
    posted: bool = False
    incomplete: bool = False


def _pages(client: Any, **arguments) -> List[Dict[str, Any]]:
    '''Return every message conversations.replies gives for the arguments.'''
    messages: List[Dict[str, Any]] = []
    cursor = None
    try:
        while True:
            page = client.conversations_replies(limit=PAGE_SIZE, cursor=cursor, **arguments)
            messages.extend(page.get('messages') or [])
            cursor = (page.get('response_metadata') or {}).get('next_cursor')
            if not (page.get('has_more') and cursor):
                return messages
    except Exception as error:
        # The error is not chained: Slack's errors can carry the response.
        raise SlackUnavailable(type(error).__name__) from None


def _is_striders(message: Dict[str, Any], bot_user_id: str) -> bool:
    return message.get('user') == bot_user_id


def _writer(message: Dict[str, Any], bot_user_id: str) -> str:
    if _is_striders(message, bot_user_id):
        return STRIDER
    if message.get('user'):
        return f"<@{message['user']}>"
    return 'An app'


def read_thread(
    client: Any, channel: str, thread_ts: str, upto_ts: str, bot_user_id: str
) -> ThreadRead:
    '''Read a thread up to and including the message sent at upto_ts.

    Raises SlackUnavailable when Slack cannot be read.
    '''
    messages = _pages(client, channel=channel, ts=thread_ts, latest=upto_ts, inclusive=True)
    limit = float(upto_ts)
    upto = sorted(
        (message for message in messages if float(message.get('ts', 0)) <= limit),
        key=lambda message: float(message['ts']),
    )
    earlier = [message for message in upto if float(message['ts']) < limit]

    return ThreadRead(
        mentioned=any(mentions(message.get('text'), bot_user_id) for message in upto),
        # A fixed sentence means the agent did not answer, so it holds no
        # memory of the thread yet. Part of a reply means it did.
        answered_before=any(
            _is_striders(message, bot_user_id)
            and (message.get('text') or '').strip() not in FIXED_SENTENCES
            for message in earlier
        ),
        earlier=[
            (_writer(message, bot_user_id), message['text'])
            for message in earlier
            if (message.get('text') or '').strip()
        ],
    )


def since_message(
    client: Any, channel: str, thread_ts: str, ts: str, bot_user_id: str
) -> SinceMessage:
    '''Read a thread from the message sent at ts onward.

    The queue hands the worker one message of a thread at a time, so anything
    STRIDEr posted in the thread after a message is its response to it.

    Raises SlackUnavailable when Slack cannot be read.
    '''
    messages = _pages(client, channel=channel, ts=thread_ts, oldest=ts, inclusive=True)
    start = float(ts)
    result = SinceMessage()

    for message in messages:
        if message.get('ts') == ts:
            result.found = True
            result.has_eyes = any(
                reaction.get('name') == EYES and bot_user_id in (reaction.get('users') or [])
                for reaction in message.get('reactions') or []
            )

    posts = sorted(
        (
            message for message in messages
            if _is_striders(message, bot_user_id) and float(message.get('ts', 0)) > start
        ),
        key=lambda message: float(message['ts']),
    )
    if posts:
        result.posted = True
        result.incomplete = incomplete_part(posts[-1].get('text'))
    return result
