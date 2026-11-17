'''Clean up after a Slack message the worker did not finish

Triggered by the held-back queue. A message arrives there when
AnswerSlackMessage crashed, ran out of time, or never ran. This function makes
sure the person is not left with the eyes reaction and nothing else.

The eyes are how it knows what is owed. The worker adds them only once it has
decided to answer, so a message without them is one nobody was promised
anything about.

It never logs a queued message. It holds what a person wrote.
'''

import time
from typing import Any, Dict, List

from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing import LambdaContext

from common.model.slack import (
    OUTCOME_CLEANED_UP,
    REASON_ALREADY_ANSWERED,
    REASON_APOLOGISED,
    REASON_NOT_STARTED,
    REASON_REPLY_INCOMPLETE,
    QueuedMessage,
)
from common.slack import api, text
from common.slack.thread import since_message

LOGGER = Logger(utc=True)


class Unfinished(Exception):
    '''The message was not cleaned up. The queue offers it again.'''


def _main(message: QueuedMessage, record: Dict[str, Any]) -> str:
    '''Do what is still owed for one message and return which case it was.'''
    since = since_message(
        api.client(), message.channel, message.reply_thread_ts(), message.ts, api.bot_user_id()
    )
    if not since.has_eyes:
        return REASON_NOT_STARTED

    if not since.posted:
        sentence, reason = text.APOLOGY, REASON_APOLOGISED
    elif since.incomplete:
        sentence, reason = text.REPLY_INCOMPLETE, REASON_REPLY_INCOMPLETE
    else:
        sentence, reason = None, REASON_ALREADY_ANSWERED

    # Post before removing the eyes. If the post fails this function runs
    # again, and the eyes are how it will know there is still something owed.
    if sentence and not api.post(message.channel, message.reply_thread_ts(), sentence):
        raise Unfinished('post')
    record['reactionRemoved'] = api.remove_eyes(message.channel, message.ts)
    return reason


def _record_handler(record: SQSRecord) -> None:
    '''Clean up after one message and write its log record.'''
    started = time.monotonic()
    message = QueuedMessage.from_json(record.body)
    log: Dict[str, Any] = {
        'correlationId': message.correlationId,
        'eventId': message.eventId,
        'channel': message.channel,
        'threadTs': message.threadTs,
        'ts': message.ts,
        'user': message.user,
    }
    try:
        log['reason'] = _main(message, log)
        log['outcome'] = OUTCOME_CLEANED_UP
    except Exception as error:
        # Only the kind of error is logged, and the error is not chained: it
        # may quote the message.
        log.update({'outcome': 'unfinished', 'errorType': type(error).__name__})
        raise Unfinished(type(error).__name__) from None
    finally:
        log['durationMs'] = int((time.monotonic() - started) * 1000)
        LOGGER.info('Slack message cleaned up', extra=log)


@LOGGER.inject_lambda_context
@event_source(data_class=SQSEvent)
def handler(event: SQSEvent, context: LambdaContext) -> Dict[str, Any]:
    '''Cleanup function entry

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
            # The message is offered again by the queue.
            failures.append({'itemIdentifier': record.message_id})
    return {'batchItemFailures': failures}
