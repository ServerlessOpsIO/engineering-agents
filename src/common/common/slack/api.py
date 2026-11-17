'''The calls the Slack receiving service makes to Slack.

Every call uses the bot token, which the deployment puts in Secrets Manager. A
call that fails or is rate limited is tried three times in all before the
caller is told Slack is unavailable.

Nothing in this module logs. It handles message text and the bot token.
'''

import os
import time
from typing import Any, Dict, Optional, Tuple

from aws_lambda_powertools.utilities import parameters
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.http_retry.builtin_handlers import (
    ConnectionErrorRetryHandler,
    RateLimitErrorRetryHandler,
    ServerErrorRetryHandler,
)

from common.slack.errors import SlackUnavailable
from common.slack.thread import EYES

TOKEN_MAX_AGE_SECONDS = 300
MEMBERSHIP_MAX_AGE_SECONDS = 3600
# Tries after the first, for every call.
RETRIES = 2
POST_TRIES = 3
SLACK_TIMEOUT_SECONDS = 10

_client: Optional[WebClient] = None
_client_token: Optional[str] = None
_bot_user_id: Optional[str] = None
# Who is a full member, by (user, team), with when it was learned.
_members: Dict[Tuple[str, str], Tuple[bool, float]] = {}


def reset() -> None:
    '''Forget everything remembered between calls. For tests.'''
    global _client, _client_token, _bot_user_id
    _client = None
    _client_token = None
    _bot_user_id = None
    _members.clear()


def _new_client(token: str) -> WebClient:
    return WebClient(
        token=token,
        timeout=SLACK_TIMEOUT_SECONDS,
        retry_handlers=[
            ConnectionErrorRetryHandler(max_retry_count=RETRIES),
            RateLimitErrorRetryHandler(max_retry_count=RETRIES),
            ServerErrorRetryHandler(max_retry_count=RETRIES),
        ],
    )


def client() -> WebClient:
    '''Return a client for the current bot token.

    The token is read again every five minutes, so a new token is picked up
    within five minutes of the deployment that brings it.
    '''
    global _client, _client_token
    token = parameters.get_secret(
        os.environ['SLACK_BOT_TOKEN_SECRET_ARN'], max_age=TOKEN_MAX_AGE_SECONDS
    )
    if _client is None or token != _client_token:
        _client = _new_client(token)
        _client_token = token
    return _client


def bot_user_id() -> str:
    '''Return STRIDEr's own user ID, which is how a mention of it is recognised.'''
    global _bot_user_id
    if _bot_user_id is None:
        try:
            _bot_user_id = client().auth_test()['user_id']
        except Exception as error:
            raise SlackUnavailable(type(error).__name__) from None
    return _bot_user_id


def is_full_member(user: str, team_id: str) -> bool:
    '''Say whether the user is a full member of the workspace.

    A guest, a person from another organisation, a bot and a deactivated
    account are not. The answer is remembered for an hour.
    '''
    known = _members.get((user, team_id))
    if known and time.monotonic() - known[1] < MEMBERSHIP_MAX_AGE_SECONDS:
        return known[0]
    try:
        profile: Dict[str, Any] = client().users_info(user=user)['user']
    except Exception as error:
        raise SlackUnavailable(type(error).__name__) from None

    member = (
        profile.get('team_id') == team_id
        and not profile.get('is_restricted')
        and not profile.get('is_ultra_restricted')
        and not profile.get('is_bot')
        and not profile.get('deleted')
    )
    _members[(user, team_id)] = (member, time.monotonic())
    return member


def add_eyes(channel: str, ts: str) -> bool:
    '''Add the eyes reaction to a message. Return whether it is now there.

    A failure is not raised: the reaction is a courtesy and must never stop a
    message being answered.
    '''
    try:
        client().reactions_add(channel=channel, timestamp=ts, name=EYES)
        return True
    except SlackApiError as error:
        return error.response.get('error') == 'already_reacted'
    except Exception:
        return False


def remove_eyes(channel: str, ts: str) -> bool:
    '''Remove the eyes reaction from a message. Return whether it is now gone.'''
    try:
        client().reactions_remove(channel=channel, timestamp=ts, name=EYES)
        return True
    except SlackApiError as error:
        return error.response.get('error') == 'no_reaction'
    except Exception:
        return False


def post(channel: str, thread_ts: str, markdown: str) -> bool:
    '''Post Markdown text in a thread. Return whether it was posted.

    Slack turns the Markdown into its own formatting.
    '''
    for attempt in range(POST_TRIES):
        try:
            client().chat_postMessage(channel=channel, thread_ts=thread_ts, markdown_text=markdown)
            return True
        except Exception:
            if attempt < POST_TRIES - 1:
                time.sleep(1)
    return False
