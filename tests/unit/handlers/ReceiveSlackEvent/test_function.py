'''Test ReceiveSlackEvent'''

import base64
import copy
import hashlib
import hmac
import json
import os
import time
from types import ModuleType
from typing import Generator

import boto3
import jsonschema
import pytest
from aws_lambda_powertools.utilities import parameters
from moto import mock_aws
from pytest_mock import MockerFixture

from common.model.slack import QueuedMessage

FN_NAME = 'ReceiveSlackEvent'
DATA_DIR = './data'
FUNC_DATA_DIR = os.path.join(DATA_DIR, 'handlers', FN_NAME)
EVENT_MENTION = os.path.join(FUNC_DATA_DIR, 'event-app-mention.json')
EVENT_URL_VERIFICATION = os.path.join(FUNC_DATA_DIR, 'event-url-verification.json')
EVENT_SCHEMA = os.path.join(FUNC_DATA_DIR, 'event.schema.json')
OUTPUT = os.path.join(FUNC_DATA_DIR, 'output.json')
OUTPUT_SCHEMA = os.path.join(FUNC_DATA_DIR, 'output.schema.json')

SIGNING_SECRET = 'test-signing-secret-value'
SECRET_NAME = 'test-slack-signing-secret'
# A word that appears in the sample message and nowhere else.
DISTINCTIVE_WORD = 'heron'
BOT = 'U0STRIDER'
SECONDS_IN_A_DAY = 86400


### Helpers
def _load(path):
    with open(path) as f:
        return json.load(f)


def ts_ago(seconds: float = 1) -> str:
    '''A Slack timestamp this many seconds before now.'''
    return f'{time.time() - seconds:.6f}'


def sign(body: str, timestamp: str, secret: str = SIGNING_SECRET) -> str:
    base = f'v0:{timestamp}:{body}'.encode('utf-8')
    return 'v0=' + hmac.new(secret.encode('utf-8'), base, hashlib.sha256).hexdigest()


def signed(event: dict, payload: dict = None, timestamp: str = None) -> dict:
    '''Return a copy of an API Gateway event carrying payload, correctly signed.'''
    event = copy.deepcopy(event)
    if payload is not None:
        event['body'] = json.dumps(payload, separators=(',', ':'))
    timestamp = timestamp or str(int(time.time()))
    event['headers']['X-Slack-Request-Timestamp'] = timestamp
    event['headers']['X-Slack-Signature'] = sign(event['body'], timestamp)
    return event


def slack_event(**changes) -> dict:
    '''The Slack payload for a mention sent a moment ago, with changes to its event.'''
    payload = json.loads(_load(EVENT_MENTION)['body'])
    payload['event']['ts'] = ts_ago()
    payload['event'].update(changes)
    payload['event'] = {k: v for k, v in payload['event'].items() if v is not None}
    return payload


def message_event(**changes) -> dict:
    '''The Slack payload for an ordinary message in a public channel.'''
    fields = {'type': 'message', 'channel_type': 'channel', 'text': f'an ordinary {DISTINCTIVE_WORD} message'}
    fields.update(changes)
    return slack_event(**fields)


### Fixtures
@pytest.fixture()
def mock_context(lambda_function_context, function_name=FN_NAME):
    '''context object'''
    return lambda_function_context(function_name)


@pytest.fixture()
def mention_event() -> dict:
    '''An API Gateway event carrying an app_mention'''
    return _load(EVENT_MENTION)


@pytest.fixture()
def url_verification_event() -> dict:
    '''An API Gateway event carrying Slack's check of the address'''
    return _load(EVENT_URL_VERIFICATION)


@pytest.fixture()
def aws_credentials(monkeypatch) -> None:
    '''Mocked AWS Credentials for moto.'''
    for name in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SECURITY_TOKEN', 'AWS_SESSION_TOKEN'):
        monkeypatch.setenv(name, 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


@pytest.fixture()
def mocked_aws(aws_credentials):
    '''Mock all AWS interactions'''
    with mock_aws():
        yield


@pytest.fixture()
def queue_url(mocked_aws) -> str:
    '''A FIFO queue like the deployed one'''
    return boto3.client('sqs', 'us-east-1').create_queue(
        QueueName='messages.fifo', Attributes={'FifoQueue': 'true'}
    )['QueueUrl']


@pytest.fixture()
def mock_fn(mocked_aws, queue_url, monkeypatch, mocker: MockerFixture) -> Generator[ModuleType, None, None]:
    '''The function module, with its secret, its queue and its settings in place'''
    secret_arn = boto3.client('secretsmanager', 'us-east-1').create_secret(
        Name=SECRET_NAME, SecretString=SIGNING_SECRET
    )['ARN']
    monkeypatch.setenv('SLACK_SIGNING_SECRET_ARN', secret_arn)
    monkeypatch.setenv('SLACK_MESSAGE_QUEUE_URL', queue_url)
    monkeypatch.setenv('MEMORY_EXPIRY_DAYS', '7')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'test')
    parameters.clear_caches()

    import src.handlers.ReceiveSlackEvent.function as fn

    mocker.patch('src.handlers.ReceiveSlackEvent.function.SQS', boto3.client('sqs', 'us-east-1'))
    yield fn
    parameters.clear_caches()


def queued(queue_url: str) -> list:
    '''Every message on the queue, as (QueuedMessage, attributes)'''
    response = boto3.client('sqs', 'us-east-1').receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=10, AttributeNames=['All']
    )
    return [
        (QueuedMessage.from_json(message['Body']), message['Attributes'])
        for message in response.get('Messages', [])
    ]


def last_record(caplog) -> dict:
    '''The fields of the function's last log record'''
    return vars(caplog.records[-1])


def everything_logged(caplog, capsys) -> str:
    '''Every log record with all its fields, and anything printed, as one string'''
    printed = capsys.readouterr()
    return '\n'.join([str(vars(record)) for record in caplog.records] + [printed.out, printed.err])


### Data validation
def test_validate_events(mention_event, url_verification_event):
    '''Test the sample events against the schema'''
    schema = _load(EVENT_SCHEMA)
    jsonschema.validate(mention_event, schema)
    jsonschema.validate(url_verification_event, schema)


def test_validate_expected_output():
    '''Test the sample output against the schema'''
    jsonschema.validate(_load(OUTPUT), _load(OUTPUT_SCHEMA))


### Only Slack can reach the agent (User Story 2)
def test_a_request_with_no_signature_is_rejected(mock_fn, mention_event, mock_context, queue_url):
    del mention_event['headers']['X-Slack-Signature']
    del mention_event['headers']['X-Slack-Request-Timestamp']

    output = mock_fn.handler(mention_event, mock_context)

    assert output['statusCode'] == 401
    assert queued(queue_url) == []


def test_a_request_with_a_wrong_signature_is_rejected(mock_fn, mention_event, mock_context, queue_url):
    event = signed(mention_event, slack_event())
    event['headers']['X-Slack-Signature'] = 'v0=' + '0' * 64

    output = mock_fn.handler(event, mock_context)

    assert output['statusCode'] == 401
    assert json.loads(output['body']) == {'message': 'Not authorised'}
    assert queued(queue_url) == []


def test_a_signature_for_a_different_body_is_rejected(mock_fn, mention_event, mock_context, queue_url):
    event = signed(mention_event, slack_event())
    event['body'] = event['body'].replace('trust boundary', 'trust  boundary')

    assert mock_fn.handler(event, mock_context)['statusCode'] == 401
    assert queued(queue_url) == []


@pytest.mark.parametrize('age', [301, -301])
def test_a_correctly_signed_request_that_is_stale_is_rejected(
    mock_fn, mention_event, mock_context, queue_url, age, capsys, caplog
):
    event = signed(mention_event, slack_event(), timestamp=str(int(time.time()) - age))

    assert mock_fn.handler(event, mock_context)['statusCode'] == 401
    assert queued(queue_url) == []
    assert last_record(caplog)['outcome'] == 'rejected_stale'


def test_header_names_in_lower_case_are_accepted(mock_fn, mention_event, mock_context, queue_url):
    event = signed(mention_event, slack_event())
    event['headers'] = {name.lower(): value for name, value in event['headers'].items()}

    assert mock_fn.handler(event, mock_context)['statusCode'] == 200
    assert len(queued(queue_url)) == 1


def test_a_body_that_is_not_json_is_rejected(mock_fn, mention_event, mock_context, queue_url):
    mention_event['body'] = 'not json'
    event = signed(mention_event)

    assert mock_fn.handler(event, mock_context)['statusCode'] == 400
    assert queued(queue_url) == []


def test_slacks_check_of_the_address_is_answered(mock_fn, url_verification_event, mock_context, queue_url):
    challenge = json.loads(url_verification_event['body'])['challenge']

    output = mock_fn.handler(signed(url_verification_event), mock_context)

    assert output['statusCode'] == 200
    assert json.loads(output['body']) == {'challenge': challenge}
    assert output['headers']['Content-Type'] == 'application/json'
    assert queued(queue_url) == []


def test_the_address_check_must_be_signed_too(mock_fn, url_verification_event, mock_context):
    assert mock_fn.handler(url_verification_event, mock_context)['statusCode'] == 401


def test_a_base64_encoded_body_is_decoded_before_it_is_checked(mock_fn, mention_event, mock_context, queue_url):
    event = signed(mention_event, slack_event())
    event['body'] = base64.b64encode(event['body'].encode('utf-8')).decode('ascii')
    event['isBase64Encoded'] = True

    assert mock_fn.handler(event, mock_context)['statusCode'] == 200
    assert len(queued(queue_url)) == 1


def test_the_output_matches_its_schema(mock_fn, mention_event, mock_context):
    output = mock_fn.handler(signed(mention_event, slack_event()), mock_context)
    jsonschema.validate(output, _load(OUTPUT_SCHEMA))


def test_nothing_secret_and_no_message_text_is_logged(mock_fn, mention_event, mock_context, capsys, caplog):
    mock_fn.handler(signed(mention_event, slack_event()), mock_context)
    rejected = signed(mention_event, slack_event())
    rejected['headers']['X-Slack-Signature'] = 'v0=' + '1' * 64
    mock_fn.handler(rejected, mock_context)

    logged = everything_logged(caplog, capsys)
    assert DISTINCTIVE_WORD not in logged
    assert 'trust boundary' not in logged
    assert SIGNING_SECRET not in logged
    assert [vars(record)['outcome'] for record in caplog.records] == ['queued', 'rejected_signature']


def test_the_log_record_has_the_agreed_fields(mock_fn, mention_event, mock_context, capsys, caplog):
    payload = slack_event()
    mock_fn.handler(signed(mention_event, payload), mock_context)

    record = last_record(caplog)

    assert record['correlationId'] == mention_event['requestContext']['requestId']
    assert record['outcome'] == 'queued'
    assert record['eventId'] == 'Ev0123ABCD'
    assert record['eventType'] == 'app_mention'
    assert record['channel'] == 'C0123ABCDEF'
    assert record['threadTs'] == payload['event']['ts']
    assert record['user'] == 'U0123ABCD'
    assert isinstance(record['durationMs'], int)


### A mention is queued (User Story 1)
def test_a_mention_is_queued_with_every_field(mock_fn, mention_event, mock_context, queue_url):
    payload = slack_event()

    output = mock_fn.handler(signed(mention_event, payload), mock_context)

    assert output['statusCode'] == 200
    assert json.loads(output['body']) == {}
    [(message, attributes)] = queued(queue_url)
    ts = payload['event']['ts']
    assert message.teamId == 'T0123ABCD'
    assert message.channel == 'C0123ABCDEF'
    assert message.channelType == 'unknown'
    assert message.ts == ts
    assert message.threadTs == ts
    assert message.isReply is False
    assert message.user == 'U0123ABCD'
    assert message.text == payload['event']['text']
    assert message.eventType == 'app_mention'
    assert message.eventId == 'Ev0123ABCD'
    assert message.correlationId == mention_event['requestContext']['requestId']
    assert message.receivedAt.endswith('+00:00')
    assert attributes['MessageGroupId'] == f'C0123ABCDEF:{ts}'
    assert attributes['MessageDeduplicationId'] == f'C0123ABCDEF:{ts}'


@pytest.mark.parametrize('payload_changes, reason', [
    ({'type': 'message', 'channel_type': 'channel'}, 'not_addressed'),
    ({'bot_id': 'B0123'}, 'not_from_a_person'),
    ({'type': 'message', 'channel_type': 'im', 'bot_id': 'B0123'}, 'not_from_a_person'),
    ({'user': None}, 'not_from_a_person'),
    ({'type': 'message', 'channel_type': 'im', 'subtype': 'message_changed'}, 'not_a_new_message'),
    ({'type': 'message', 'channel_type': 'im', 'subtype': 'message_deleted'}, 'not_a_new_message'),
    ({'type': 'message', 'channel_type': 'channel', 'subtype': 'channel_join'}, 'not_a_new_message'),
    ({'type': 'message', 'channel_type': 'im', 'subtype': 'bot_message'}, 'not_a_new_message'),
    ({'edited': {'user': 'U0123ABCD', 'ts': '1731790001.000000'}}, 'not_a_new_message'),
    ({'type': 'reaction_added'}, 'not_a_message'),
    ({'type': 'message', 'channel_type': 'mpim', 'thread_ts': '1731780000.000001'}, 'not_addressed'),
])
def test_what_is_not_for_strider_is_acknowledged_and_ignored(
    mock_fn, mention_event, mock_context, queue_url, capsys, payload_changes, reason, caplog
):
    output = mock_fn.handler(signed(mention_event, slack_event(**payload_changes)), mock_context)

    assert output['statusCode'] == 200
    assert queued(queue_url) == []
    record = last_record(caplog)
    assert (record['outcome'], record['reason']) == ('ignored', reason)


def test_a_request_that_is_not_an_event_is_acknowledged_and_ignored(mock_fn, mention_event, mock_context, queue_url):
    output = mock_fn.handler(signed(mention_event, {'type': 'app_rate_limited'}), mock_context)

    assert output['statusCode'] == 200
    assert queued(queue_url) == []


def test_the_same_event_delivered_twice_is_queued_once(mock_fn, mention_event, mock_context, queue_url):
    payload = slack_event()
    retry = signed(mention_event, payload)
    retry['headers']['X-Slack-Retry-Num'] = '1'

    assert mock_fn.handler(signed(mention_event, payload), mock_context)['statusCode'] == 200
    assert mock_fn.handler(retry, mock_context)['statusCode'] == 200

    assert len(queued(queue_url)) == 1


def test_a_queue_that_cannot_be_reached_gives_500_so_slack_tries_again(
    mock_fn, mention_event, mock_context, monkeypatch, capsys, caplog
):
    monkeypatch.setenv('SLACK_MESSAGE_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/012345678910/missing.fifo')

    output = mock_fn.handler(signed(mention_event, slack_event()), mock_context)

    assert output['statusCode'] == 500
    assert last_record(caplog)['outcome'] == 'error'
    assert DISTINCTIVE_WORD not in everything_logged(caplog, capsys)


### A conversation continues in its thread (User Story 4)
def test_a_reply_in_a_channel_thread_is_queued_for_the_worker_to_check(
    mock_fn, mention_event, mock_context, queue_url
):
    thread_ts = ts_ago(600)
    payload = message_event(thread_ts=thread_ts)

    mock_fn.handler(signed(mention_event, payload), mock_context)

    [(message, attributes)] = queued(queue_url)
    assert message.isReply is True
    assert message.threadTs == thread_ts
    assert message.channelType == 'channel'
    assert message.eventType == 'message'
    assert attributes['MessageGroupId'] == f'C0123ABCDEF:{thread_ts}'


def test_a_reply_in_a_private_channel_thread_is_queued_too(mock_fn, mention_event, mock_context, queue_url):
    payload = message_event(channel_type='group', thread_ts=ts_ago(600))
    mock_fn.handler(signed(mention_event, payload), mock_context)
    assert len(queued(queue_url)) == 1


def test_a_reply_also_sent_to_the_channel_and_a_message_with_a_file_are_queued(
    mock_fn, mention_event, mock_context, queue_url
):
    thread_ts = ts_ago(600)
    for subtype, seconds in (('thread_broadcast', 3), ('file_share', 2)):
        payload = message_event(subtype=subtype, thread_ts=thread_ts, ts=ts_ago(seconds))
        mock_fn.handler(signed(mention_event, payload), mock_context)
    assert len(queued(queue_url)) == 2


def test_the_parent_of_a_thread_is_not_a_reply(mock_fn, mention_event, mock_context, queue_url):
    ts = ts_ago()
    mock_fn.handler(signed(mention_event, message_event(ts=ts, thread_ts=ts)), mock_context)
    assert queued(queue_url) == []


def test_a_reply_in_a_thread_older_than_the_agents_memory_is_not_queued(
    mock_fn, mention_event, mock_context, queue_url, capsys, caplog
):
    payload = message_event(thread_ts=ts_ago(8 * SECONDS_IN_A_DAY))

    mock_fn.handler(signed(mention_event, payload), mock_context)

    assert queued(queue_url) == []
    record = last_record(caplog)
    assert (record['outcome'], record['reason']) == ('ignored', 'thread_expired')


def test_a_mention_in_an_old_thread_is_still_queued_so_the_person_can_be_told(
    mock_fn, mention_event, mock_context, queue_url
):
    payload = slack_event(thread_ts=ts_ago(8 * SECONDS_IN_A_DAY))
    mock_fn.handler(signed(mention_event, payload), mock_context)
    assert len(queued(queue_url)) == 1


def test_a_mention_and_its_message_twin_are_queued_once(mock_fn, mention_event, mock_context, queue_url):
    thread_ts, ts = ts_ago(600), ts_ago()
    text = f'<@{BOT}> and another thing'
    twin = message_event(thread_ts=thread_ts, ts=ts, text=text)
    twin['event_id'] = 'Ev0TWIN'
    mention = slack_event(thread_ts=thread_ts, ts=ts, text=text)

    mock_fn.handler(signed(mention_event, twin), mock_context)
    mock_fn.handler(signed(mention_event, mention), mock_context)

    assert len(queued(queue_url)) == 1


### A direct message (User Story 5)
def test_a_direct_message_is_queued_without_a_mention(mock_fn, mention_event, mock_context, queue_url):
    payload = message_event(channel_type='im', channel='D0123ABCDEF')

    mock_fn.handler(signed(mention_event, payload), mock_context)

    [(message, attributes)] = queued(queue_url)
    assert message.channelType == 'im'
    assert message.isReply is False
    assert message.threadTs == message.ts
    # The whole direct message is one group, so it is answered in order.
    assert attributes['MessageGroupId'] == 'D0123ABCDEF'


def test_a_reply_in_a_direct_message_thread_is_queued_however_old_the_thread(
    mock_fn, mention_event, mock_context, queue_url
):
    payload = message_event(channel_type='im', channel='D0123ABCDEF', thread_ts=ts_ago(8 * SECONDS_IN_A_DAY))

    mock_fn.handler(signed(mention_event, payload), mock_context)

    [(message, _)] = queued(queue_url)
    assert message.isReply is True


### Old messages (User Story 6)
def test_a_message_more_than_four_minutes_old_is_ignored(mock_fn, mention_event, mock_context, queue_url, capsys, caplog):
    mock_fn.handler(signed(mention_event, slack_event(ts=ts_ago(241))), mock_context)

    assert queued(queue_url) == []
    record = last_record(caplog)
    assert (record['outcome'], record['reason']) == ('ignored', 'too_old')


def test_a_message_just_under_four_minutes_old_is_queued(mock_fn, mention_event, mock_context, queue_url):
    mock_fn.handler(signed(mention_event, slack_event(ts=ts_ago(235))), mock_context)
    assert len(queued(queue_url)) == 1
