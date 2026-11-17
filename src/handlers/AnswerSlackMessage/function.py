'''Answer a Slack message

The worker of the Slack receiving service. It takes one queued message at a
time, decides whether STRIDEr should answer it, asks the agent, and posts the
reply in the thread.

It handles each message once. There is no record of what has been answered,
so running twice could post twice; a message this function does not finish
goes to the held-back queue, where CleanUpSlackMessage deals with it.

It never logs a queued message, a prompt or a reply. They hold what people
wrote.
'''

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing import LambdaContext

from common import agentcore
from common.model.slack import (
    OUTCOME_ANSWERED,
    OUTCOME_DECLINED,
    OUTCOME_FAILED,
    REASON_AGENT_FAILED,
    REASON_IDENTITY_UNKNOWN,
    REASON_MEMBERSHIP_UNKNOWN,
    REASON_NOTHING_ASKED,
    REASON_NOT_MEMBER,
    REASON_NOT_STRIDER_THREAD,
    REASON_REPLY_NOT_POSTED,
    REASON_THREAD_EXPIRED,
    REASON_THREAD_UNREADABLE,
    REASON_TOO_LONG,
    QueuedMessage,
)
from common.slack import api, text
from common.slack.errors import SlackUnavailable
from common.slack.thread import read_thread, thread_expired

LOGGER = Logger(utc=True)

ATTEMPTS = 2
PAUSE_BETWEEN_ATTEMPTS_SECONDS = 2

Outcome = Tuple[str, Optional[str]]


class Unfinished(Exception):
    '''The message was not dealt with. The queue moves it to the held-back queue.'''


def _is_member(message: QueuedMessage) -> Optional[Outcome]:
    '''Return None when the writer is a full member, otherwise how handling ends.'''
    try:
        if api.is_full_member(message.user, message.teamId):
            return None
    except SlackUnavailable:
        return OUTCOME_FAILED, REASON_MEMBERSHIP_UNKNOWN
    return OUTCOME_DECLINED, REASON_NOT_MEMBER


def _say(message: QueuedMessage, sentence: str, record: Dict[str, Any]) -> None:
    '''Post one fixed sentence in the thread, with the eyes on while it is posted.'''
    record['reactionAdded'] = api.add_eyes(message.channel, message.ts)
    try:
        api.post(message.channel, message.threadTs, sentence)
    finally:
        record['reactionRemoved'] = api.remove_eyes(message.channel, message.ts)


def _ask_agent(message: QueuedMessage, prompt: str, record: Dict[str, Any]) -> Optional[agentcore.AgentReply]:
    '''Ask the agent, and once more if it fails. Return its reply, or None.'''
    session_id = message.session_id()
    record['sessionId'] = session_id
    for attempt in range(1, ATTEMPTS + 1):
        record['attempts'] = attempt
        try:
            reply = agentcore.ask(session_id, prompt, message.user)
            record['agentRequestId'] = reply.request_id
            return reply
        except agentcore.AgentFailed:
            if attempt < ATTEMPTS:
                time.sleep(PAUSE_BETWEEN_ATTEMPTS_SECONDS)
    return None


def _answer(
    message: QueuedMessage,
    bot_user_id: str,
    addressed: bool,
    earlier: List[Tuple[str, str]],
    record: Dict[str, Any],
) -> Outcome:
    '''Get the agent's answer and post it. The eyes are already on the message.'''
    def post(sentence: str) -> bool:
        return api.post(message.channel, message.threadTs, sentence)

    asked = text.strip_mention(message.text, bot_user_id)
    if not asked:
        # A file on its own in one of STRIDEr's threads is not a question.
        if addressed:
            post(text.NOTHING_ASKED)
        return OUTCOME_DECLINED, REASON_NOTHING_ASKED

    try:
        prompt, dropped = text.build_prompt(asked, earlier, int(os.environ['MAX_PROMPT_CHARS']))
    except text.TooLong:
        post(text.TOO_LONG)
        return OUTCOME_DECLINED, REASON_TOO_LONG
    record['contextMessages'] = len(earlier) - dropped
    record['contextDropped'] = dropped

    reply = _ask_agent(message, prompt, record)
    if reply is None:
        post(text.APOLOGY)
        return OUTCOME_FAILED, REASON_AGENT_FAILED
    if reply.kind == agentcore.KIND_INPUT_REJECTION:
        post(text.TOO_LONG)
        return OUTCOME_DECLINED, REASON_TOO_LONG

    parts = text.split_reply(reply.text)
    posted = 0
    for part in parts:
        if not post(part):
            break
        posted += 1
    record['replyParts'] = posted
    if posted < len(parts):
        post(text.REPLY_INCOMPLETE if posted else text.APOLOGY)
        return OUTCOME_FAILED, REASON_REPLY_NOT_POSTED
    return OUTCOME_ANSWERED, None


def _main(message: QueuedMessage, record: Dict[str, Any]) -> Outcome:
    '''Decide whether to answer one message, and answer it.'''
    try:
        bot_user_id = api.bot_user_id()
    except SlackUnavailable:
        return OUTCOME_FAILED, REASON_IDENTITY_UNKNOWN

    mentioned = text.mentions(message.text, bot_user_id)
    addressed = mentioned or message.is_direct_message()

    # A thread older than the agent's memory is no longer STRIDEr's. This is
    # checked before the thread is read, so an old thread costs no call to Slack.
    if message.isReply and thread_expired(
        message.threadTs, int(os.environ['MEMORY_EXPIRY_DAYS']), time.time()
    ):
        if not addressed:
            return OUTCOME_DECLINED, REASON_THREAD_EXPIRED
        stop = _is_member(message)
        if stop:
            return stop
        _say(message, text.START_AGAIN, record)
        return OUTCOME_DECLINED, REASON_THREAD_EXPIRED

    # Only a reply in a channel thread needs the thread read: to see whether
    # STRIDEr was mentioned there, and to give the agent the earlier messages
    # the first time STRIDEr answers in it.
    earlier: List[Tuple[str, str]] = []
    if message.isReply and not message.is_direct_message():
        try:
            thread = read_thread(api.client(), message.channel, message.threadTs, message.ts, bot_user_id)
        except SlackUnavailable:
            if not mentioned:
                # The thread may not be STRIDEr's, so nothing is shown.
                return OUTCOME_FAILED, REASON_THREAD_UNREADABLE
            stop = _is_member(message)
            if stop:
                return stop
            _say(message, text.APOLOGY, record)
            return OUTCOME_FAILED, REASON_THREAD_UNREADABLE
        record['threadRead'] = True
        if not thread.mentioned:
            return OUTCOME_DECLINED, REASON_NOT_STRIDER_THREAD
        if not thread.answered_before:
            earlier = thread.earlier

    stop = _is_member(message)
    if stop:
        return stop

    record['reactionAdded'] = api.add_eyes(message.channel, message.ts)
    try:
        return _answer(message, bot_user_id, addressed, earlier, record)
    finally:
        # Whatever happened, the eyes must not be left to say "working on it".
        record['reactionRemoved'] = api.remove_eyes(message.channel, message.ts)


def _record_handler(record: SQSRecord) -> None:
    '''Handle one queued message and write its log record.'''
    started = time.monotonic()
    message = QueuedMessage.from_json(record.body)
    log: Dict[str, Any] = {
        'correlationId': message.correlationId,
        'eventId': message.eventId,
        'channel': message.channel,
        'threadTs': message.threadTs,
        'ts': message.ts,
        'user': message.user,
        'threadRead': False,
    }
    try:
        log['outcome'], log['reason'] = _main(message, log)
    except Exception as error:
        # Only the kind of error is logged, and the error is not chained: it
        # may quote the message.
        log.update({'outcome': 'unfinished', 'errorType': type(error).__name__})
        raise Unfinished(type(error).__name__) from None
    finally:
        log['durationMs'] = int((time.monotonic() - started) * 1000)
        LOGGER.info('Slack message handled', extra=log)


@LOGGER.inject_lambda_context
@event_source(data_class=SQSEvent)
def handler(event: SQSEvent, context: LambdaContext) -> Dict[str, Any]:
    '''Answer function entry

    Returns the messages that were not dealt with, which the queue then treats
    as failed. A failure is reported this way and not raised, so that nothing
    about the message is logged. Once one message of a batch fails the rest
    are reported too, to keep a thread's messages in order.
    '''
    failures: List[Dict[str, str]] = []
    for record in event.records:
        if failures:
            failures.append({'itemIdentifier': record.message_id})
            continue
        try:
            _record_handler(record)
        except Unfinished:
            # The message goes to the held-back queue.
            failures.append({'itemIdentifier': record.message_id})
    return {'batchItemFailures': failures}
