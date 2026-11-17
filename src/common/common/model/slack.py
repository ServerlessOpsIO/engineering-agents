'''Records the Slack receiving service passes between its parts.

The queued message carries the text of a Slack message. It must never be
logged; see docs/handbook/09-slack-messaging.md.
'''

import json
import re
from dataclasses import asdict, dataclass

SESSION_ID_MIN_CHARS = 33
SESSION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')

# Kinds of event the front door queues.
EVENT_APP_MENTION = 'app_mention'
EVENT_MESSAGE = 'message'

# Where a message was written. An app_mention event does not say.
CHANNEL_TYPE_IM = 'im'
CHANNEL_TYPE_UNKNOWN = 'unknown'

# How the worker's handling of one message ends.
OUTCOME_ANSWERED = 'answered'
OUTCOME_DECLINED = 'declined'
OUTCOME_FAILED = 'failed'
# How the cleanup function's handling of one message ends.
OUTCOME_CLEANED_UP = 'cleaned_up'

REASON_NOT_STRIDER_THREAD = 'not_strider_thread'
REASON_NOT_MEMBER = 'not_member'
REASON_THREAD_EXPIRED = 'thread_expired'
REASON_TOO_LONG = 'too_long'
REASON_NOTHING_ASKED = 'nothing_asked'
REASON_AGENT_FAILED = 'agent_failed'
REASON_THREAD_UNREADABLE = 'thread_unreadable'
REASON_MEMBERSHIP_UNKNOWN = 'membership_unknown'
REASON_IDENTITY_UNKNOWN = 'identity_unknown'
REASON_REPLY_NOT_POSTED = 'reply_not_posted'

REASON_NOT_STARTED = 'not_started'
REASON_ALREADY_ANSWERED = 'already_answered'
REASON_APOLOGISED = 'apologised'
REASON_REPLY_INCOMPLETE = 'reply_incomplete'


@dataclass
class QueuedMessage:
    '''One Slack message that may be worth answering.'''
    teamId: str
    channel: str
    channelType: str
    ts: str
    threadTs: str
    isReply: bool
    user: str
    text: str
    eventType: str
    eventId: str
    correlationId: str
    receivedAt: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, body: str) -> 'QueuedMessage':
        return cls(**json.loads(body))

    def message_group_id(self) -> str:
        '''One group per thread, so a thread's messages are handled in order.'''
        return f'{self.channel}:{self.threadTs}'

    def deduplication_id(self) -> str:
        '''One ID per message, so a second delivery is dropped by the queue.'''
        return f'{self.channel}:{self.ts}'

    def session_id(self) -> str:
        '''The agent session for this message's thread.

        It is worked out from the thread alone, so every message in a thread
        gets the same session and different threads get different ones.
        '''
        session_id = 'slack-{}-{}-{}'.format(
            self.teamId, self.channel, self.threadTs.replace('.', '-')
        )
        if len(session_id) < SESSION_ID_MIN_CHARS:
            raise ValueError('The session ID is shorter than AgentCore accepts')
        if not SESSION_ID_PATTERN.match(session_id):
            raise ValueError('The session ID has a character AgentCore may not accept')
        return session_id

    def is_direct_message(self) -> bool:
        return self.channelType == CHANNEL_TYPE_IM
