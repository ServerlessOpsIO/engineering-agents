'''The call the Slack receiving service makes to the agent.

The agent is the AgentCore runtime in this stack. It is called with the
caller's IAM role; see docs/handbook/04-architecture.md for its interface.

Nothing in this module logs. It handles prompts and replies.
'''

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config

# One attempt may take this long. The SDK's own retries are off: the worker
# decides when to try again.
ATTEMPT_SECONDS = 100
CONNECT_SECONDS = 5

KIND_ANSWER = 'answer'
KIND_INPUT_REJECTION = 'input_rejection'
# The agent judged that the message needed nothing from it. Nothing is posted.
KIND_NO_REPLY = 'no_reply'

CHANNEL_THREAD = 'channel_thread'
DIRECT_MESSAGE = 'direct_message'

_client: Optional[Any] = None


class AgentFailed(Exception):
    '''The agent did not answer, or its answer could not be read.'''


@dataclass
class AgentReply:
    '''What the agent returned.'''
    kind: str
    text: str
    request_id: Optional[str]
    # Documents to deliver as files: each has a filename, a title and its Markdown.
    documents: List[Dict[str, str]] = field(default_factory=list)


def client() -> Any:
    global _client
    if _client is None:
        _client = boto3.client(
            'bedrock-agentcore',
            config=Config(
                read_timeout=ATTEMPT_SECONDS,
                connect_timeout=CONNECT_SECONDS,
                retries={'total_max_attempts': 1},
            ),
        )
    return _client


def _documents(body: Dict[str, Any]) -> List[Dict[str, str]]:
    '''Return the documents in a reply, keeping only those that are whole.'''
    documents = body.get('documents')
    if not isinstance(documents, list):
        return []
    return [
        {key: document[key] for key in ('filename', 'title', 'markdown')}
        for document in documents
        if isinstance(document, dict)
        and all(isinstance(document.get(key), str) and document[key]
                for key in ('filename', 'title', 'markdown'))
    ]


def ask(
    session_id: str,
    prompt: str,
    slack_user_id: str,
    *,
    speaker_name: Optional[str] = None,
    conversation_type: Optional[str] = None,
    addressed: Optional[bool] = None,
    message_id: Optional[str] = None,
    thread_ends_at: Optional[str] = None,
) -> AgentReply:
    '''Ask the agent once and return its reply.

    speaker_name is the writer's name as Slack displays it. conversation_type
    and addressed let the agent decide whether it may stay quiet. message_id is
    the same on a second attempt at one message, so the agent records what the
    message leads to once. thread_ends_at is when a channel thread stops being
    answered. Any of them left as None is not sent.

    No actorId is sent. The agent keeps memory by session and by actor, so
    sending the person as the actor would give each person in a thread a
    conversation of their own. slackUserId is information for a later feature;
    the agent ignores it today.

    Raises AgentFailed for anything but an answer or an input rejection.
    '''
    fields = {
        'prompt': prompt,
        'slackUserId': slack_user_id,
        'speakerName': speaker_name,
        'conversationType': conversation_type,
        'addressed': addressed,
        'messageId': message_id,
        'threadEndsAt': thread_ends_at,
    }
    payload = json.dumps({key: value for key, value in fields.items() if value is not None})
    try:
        response = client().invoke_agent_runtime(
            agentRuntimeArn=os.environ['AGENT_RUNTIME_ARN'],
            runtimeSessionId=session_id,
            payload=payload.encode('utf-8'),
            contentType='application/json',
            accept='application/json',
        )
        status = response.get('statusCode')
        body = json.loads(response['response'].read())
    except Exception as error:
        # The error is not chained: it may quote the prompt.
        raise AgentFailed(type(error).__name__) from None

    request_id = body.get('requestId') if isinstance(body, dict) else None
    if status not in (None, 200) or not isinstance(body, dict):
        raise AgentFailed(f'status {status}')
    if body.get('kind') not in (KIND_ANSWER, KIND_INPUT_REJECTION, KIND_NO_REPLY):
        raise AgentFailed(str(body.get('kind')))
    text = (body.get('text') or '').strip()
    if body['kind'] == KIND_ANSWER and not text:
        raise AgentFailed('empty answer')
    documents = _documents(body) if body['kind'] == KIND_ANSWER else []
    return AgentReply(kind=body['kind'], text=text, request_id=request_id, documents=documents)
