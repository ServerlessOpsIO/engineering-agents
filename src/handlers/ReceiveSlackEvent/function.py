'''Receive Slack events

The front door of the Slack receiving service. It accepts a request only when
Slack's signature proves Slack sent it, answers Slack at once, and puts each
message that may be worth answering on a queue.

It never logs the request. The request holds what people wrote.
'''

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import boto3
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.data_classes import event_source, APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext

from common.model.slack import (
    CHANNEL_TYPE_IM,
    CHANNEL_TYPE_UNKNOWN,
    EVENT_APP_MENTION,
    EVENT_MESSAGE,
    QueuedMessage,
)
from common.slack.signature import MAX_AGE_SECONDS, verify
from common.slack.thread import thread_expired
from common.util.dataclasses import lambda_dataclass_response

LOGGER = Logger(utc=True)

SQS = boto3.client('sqs')

SECRET_MAX_AGE_SECONDS = 300
# Slack sends an event again after 5 minutes when it had no answer, which is
# outside the queue's 5-minute memory of what it has seen. Ignoring anything
# older than this means that late copy is never answered a second time.
MAX_MESSAGE_AGE_SECONDS = 240
# Kinds of message a person can write. Every other kind is an edit, a deletion
# or a notice Slack writes itself.
ANSWERED_SUBTYPES = (None, 'file_share', 'thread_broadcast')
CHANNEL_TYPES_WITH_THREADS = ('channel', 'group')

JSON_HEADERS = {'Content-Type': 'application/json'}


@dataclass
class Output:
    '''Function response'''
    statusCode: int
    body: str
    headers: Dict[str, str] = field(default_factory=lambda: dict(JSON_HEADERS))


def _output(status: int, body: Dict[str, Any]) -> Output:
    return Output(statusCode=status, body=json.dumps(body))


def _signing_secret() -> str:
    return parameters.get_secret(
        os.environ['SLACK_SIGNING_SECRET_ARN'],
        max_age=SECRET_MAX_AGE_SECONDS,
    )


def _classify(
    payload: Dict[str, Any], correlation_id: str, now: float, record: Dict[str, Any]
) -> Tuple[Optional[QueuedMessage], Optional[str]]:
    '''Decide, from the event alone, whether a message may be worth answering.

    Returns the message to queue, or None and why it is ignored. The worker
    decides the two rules that need Slack to be asked.
    '''
    event = payload.get('event') or {}
    event_type = event.get('type')
    channel = event.get('channel')
    ts = event.get('ts')
    thread_ts = event.get('thread_ts') or ts
    user = event.get('user')
    record.update({
        'eventId': payload.get('event_id'),
        'eventType': event_type,
        'channel': channel,
        'threadTs': thread_ts,
        'user': user,
    })

    if event_type not in (EVENT_APP_MENTION, EVENT_MESSAGE):
        return None, 'not_a_message'
    if event.get('bot_id') or not user:
        return None, 'not_from_a_person'
    if event.get('subtype') not in ANSWERED_SUBTYPES or event.get('edited'):
        return None, 'not_a_new_message'
    if not channel or not ts:
        return None, 'incomplete'
    if now - float(ts) > MAX_MESSAGE_AGE_SECONDS:
        return None, 'too_old'

    is_reply = thread_ts != ts
    if event_type == EVENT_APP_MENTION:
        channel_type = CHANNEL_TYPE_UNKNOWN
    else:
        channel_type = event.get('channel_type')
        if channel_type == CHANNEL_TYPE_IM:
            pass
        elif channel_type in CHANNEL_TYPES_WITH_THREADS and is_reply:
            # A reply in an old thread is no longer STRIDEr's to follow. A
            # mention there arrives as an app_mention and is queued above.
            if thread_expired(thread_ts, int(os.environ['MEMORY_EXPIRY_DAYS']), now):
                return None, 'thread_expired'
        else:
            # A top-level message in a channel. If it mentions STRIDEr, Slack
            # also sends it as an app_mention.
            return None, 'not_addressed'

    return QueuedMessage(
        teamId=payload.get('team_id') or '',
        channel=channel,
        channelType=channel_type,
        ts=ts,
        threadTs=thread_ts,
        isReply=is_reply,
        user=user,
        text=event.get('text') or '',
        eventType=event_type,
        eventId=payload.get('event_id') or '',
        correlationId=correlation_id,
        receivedAt=datetime.now(timezone.utc).isoformat(),
    ), None


def _main(event: APIGatewayProxyEvent, record: Dict[str, Any]) -> Output:
    '''Check the request, answer Slack, and queue the message if there is one.'''
    now = time.time()
    headers = event.headers
    timestamp = headers.get('x-slack-request-timestamp')
    retry = headers.get('x-slack-retry-num')
    if retry:
        record['retryNum'] = retry
    body = event.decoded_body or ''

    if not verify(_signing_secret(), timestamp, headers.get('x-slack-signature'), body, now):
        stale = (timestamp or '').isdigit() and abs(now - int(timestamp)) > MAX_AGE_SECONDS
        record['outcome'] = 'rejected_stale' if stale else 'rejected_signature'
        return _output(401, {'message': 'Not authorised'})

    try:
        payload = json.loads(body)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        record['outcome'] = 'rejected_body'
        return _output(400, {'message': 'Bad request'})

    if payload.get('type') == 'url_verification':
        record['outcome'] = 'url_verified'
        return _output(200, {'challenge': payload.get('challenge')})

    if payload.get('type') != 'event_callback':
        record.update({'outcome': 'ignored', 'reason': 'not_an_event'})
        return _output(200, {})

    message, reason = _classify(payload, record['correlationId'], now, record)
    if message is None:
        record.update({'outcome': 'ignored', 'reason': reason})
        return _output(200, {})

    try:
        SQS.send_message(
            QueueUrl=os.environ['SLACK_MESSAGE_QUEUE_URL'],
            MessageBody=message.to_json(),
            MessageGroupId=message.message_group_id(),
            MessageDeduplicationId=message.deduplication_id(),
        )
    except Exception as error:  # Slack sends the event again when it gets a 500.
        # Only the kind of error is logged. The error may quote the message.
        record.update({'outcome': 'error', 'errorType': type(error).__name__})
        return _output(500, {'message': 'Try again'})

    record['outcome'] = 'queued'
    return _output(200, {})


@LOGGER.inject_lambda_context
@event_source(data_class=APIGatewayProxyEvent)
@lambda_dataclass_response
def handler(event: APIGatewayProxyEvent, context: LambdaContext) -> Output:
    '''Receive function entry'''
    started = time.monotonic()
    record: Dict[str, Any] = {'correlationId': event.request_context.request_id}

    output = _main(event, record)

    record['durationMs'] = int((time.monotonic() - started) * 1000)
    LOGGER.info('Slack request handled', extra=record)
    return output
