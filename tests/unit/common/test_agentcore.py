'''Tests for the call the Slack receiving service makes to the agent.'''

import io
import json

import pytest

from common import agentcore
from common.agentcore import AgentFailed

ARN = 'arn:aws:bedrock-agentcore:us-east-1:012345678910:runtime/engineering_agents_main-abc123'
SESSION = 'slack-T0123ABCD-C0123ABCDEF-1731790000-111111'


class FakeRuntime:
    '''Stands in for the bedrock-agentcore client.'''

    def __init__(self, body=None, status=200, error=None):
        self.body = body
        self.status = status
        self.error = error
        self.calls = []

    def invoke_agent_runtime(self, **arguments):
        self.calls.append(arguments)
        if self.error:
            raise self.error
        raw = self.body if isinstance(self.body, bytes) else json.dumps(self.body).encode('utf-8')
        return {'statusCode': self.status, 'contentType': 'application/json', 'response': io.BytesIO(raw)}


@pytest.fixture()
def runtime(mocker, monkeypatch):
    monkeypatch.setenv('AGENT_RUNTIME_ARN', ARN)

    def use(fake):
        mocker.patch('common.agentcore.client', return_value=fake)
        return fake
    return use


def test_the_agent_is_asked_with_the_threads_session_and_no_actor(runtime):
    fake = runtime(FakeRuntime({'kind': 'answer', 'text': 'a reply', 'requestId': 'r-1'}))

    agentcore.ask(SESSION, 'a question', 'U0123ABCD')

    [call] = fake.calls
    assert call['agentRuntimeArn'] == ARN
    assert call['runtimeSessionId'] == SESSION
    payload = json.loads(call['payload'])
    assert payload == {'prompt': 'a question', 'slackUserId': 'U0123ABCD'}
    # The agent keeps memory by actor. Sending one would split a thread's conversation.
    assert 'actorId' not in payload
    assert 'runtimeUserId' not in call


def test_an_answer_is_returned_with_the_agents_request_id(runtime):
    runtime(FakeRuntime({'kind': 'answer', 'text': '  a reply\n', 'requestId': 'r-1'}))

    reply = agentcore.ask(SESSION, 'a question', 'U1')

    assert (reply.kind, reply.text, reply.request_id) == ('answer', 'a reply', 'r-1')


def test_an_input_rejection_is_returned_and_is_not_a_failure(runtime):
    runtime(FakeRuntime({'kind': 'input_rejection', 'text': 'The prompt is too long.', 'requestId': 'r-2'}))
    assert agentcore.ask(SESSION, 'a question', 'U1').kind == 'input_rejection'


@pytest.mark.parametrize('fake', [
    FakeRuntime({'kind': 'error', 'text': 'The agent could not produce a reply.', 'requestId': 'r-3'}, status=500),
    FakeRuntime({'kind': 'error', 'text': 'The agent could not produce a reply.'}),
    FakeRuntime({'kind': 'answer', 'text': 'a reply'}, status=500),
    FakeRuntime(error=RuntimeError('RuntimeClientError: a question')),
    FakeRuntime(error=TimeoutError('read timed out')),
    FakeRuntime(b'not json'),
    FakeRuntime(['a', 'list']),
    FakeRuntime({'kind': 'something_new', 'text': 'x'}),
    FakeRuntime({'kind': 'answer', 'text': '   '}),
])
def test_anything_but_an_answer_or_a_rejection_is_a_failed_attempt(runtime, fake):
    runtime(fake)
    with pytest.raises(AgentFailed):
        agentcore.ask(SESSION, 'a question', 'U1')


def test_a_failure_does_not_carry_the_prompt(runtime):
    runtime(FakeRuntime(error=RuntimeError('could not process: a distinctive question')))
    with pytest.raises(AgentFailed) as raised:
        agentcore.ask(SESSION, 'a distinctive question', 'U1')
    assert 'distinctive' not in str(raised.value)
    assert raised.value.__cause__ is None


def test_one_attempt_may_take_100_seconds_and_the_sdk_does_not_retry(monkeypatch):
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setattr(agentcore, '_client', None)

    config = agentcore.client().meta.config

    assert config.read_timeout == 100
    assert config.retries['total_max_attempts'] == 1
    monkeypatch.setattr(agentcore, '_client', None)


### Spec 008: who is speaking, no reply, documents
def test_the_new_fields_are_sent_and_left_out_when_not_given(runtime):
    fake = runtime(FakeRuntime({'kind': 'answer', 'text': 'a reply', 'requestId': 'r-1'}))

    agentcore.ask(
        SESSION, 'a question', 'U1', speaker_name='Ana Souza',
        conversation_type=agentcore.CHANNEL_THREAD, addressed=False,
        message_id='C1:1731790000.111111', thread_ends_at='2026-11-28T10:00:00Z',
    )
    agentcore.ask(SESSION, 'a question', 'U1', conversation_type=agentcore.DIRECT_MESSAGE)

    full, bare = [json.loads(call['payload']) for call in fake.calls]
    assert full == {
        'prompt': 'a question', 'slackUserId': 'U1', 'speakerName': 'Ana Souza',
        'conversationType': 'channel_thread', 'addressed': False,
        'messageId': 'C1:1731790000.111111', 'threadEndsAt': '2026-11-28T10:00:00Z',
    }
    assert bare == {'prompt': 'a question', 'slackUserId': 'U1', 'conversationType': 'direct_message'}
    assert 'actorId' not in full


def test_no_reply_is_a_reply_with_no_text_and_not_a_failure(runtime):
    runtime(FakeRuntime({'kind': 'no_reply', 'text': '', 'requestId': 'r-1'}))
    reply = agentcore.ask(SESSION, 'a question', 'U1')
    assert (reply.kind, reply.text, reply.documents) == ('no_reply', '', [])


def test_documents_come_back_with_an_answer(runtime):
    document = {'filename': 'threat-model-shop.md', 'title': 'Threat model: Shop', 'markdown': '# x'}
    runtime(FakeRuntime({'kind': 'answer', 'text': 'attached', 'requestId': 'r-1',
                         'documents': [document, {'filename': 'broken.md'}, 'not a document']}))
    assert agentcore.ask(SESSION, 'a question', 'U1').documents == [document]


def test_a_reply_without_documents_has_none(runtime):
    runtime(FakeRuntime({'kind': 'answer', 'text': 'a reply', 'documents': 'nonsense'}))
    assert agentcore.ask(SESSION, 'a question', 'U1').documents == []
