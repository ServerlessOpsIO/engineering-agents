"""The calls this project makes to Slack's Web API, and what each failure means.

Only the standard library is used. No token ever appears in an error raised here:
errors carry a failure kind and Slack's error code, nothing else.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from slack_app import SlackAppError

API = "https://slack.com/api/"
TIMEOUT_SECONDS = 30

# Slack error codes that mean the same thing whichever token was used.
UNAVAILABLE = {
    "ratelimited", "rate_limited", "service_unavailable", "internal_error", "fatal_error",
    "request_timeout",
}
# Codes that mean the token was refused.
REFUSED = {
    "invalid_auth", "not_authed", "token_expired", "token_revoked", "account_inactive",
    "not_allowed_token_type",
}


def _http(url, headers, body):
    """Send one POST and return (status, headers with lowercase names, body bytes)."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return (
                response.status,
                {name.lower(): value for name, value in response.headers.items()},
                response.read(),
            )
    except urllib.error.HTTPError as error:
        return error.code, {}, b""
    except (urllib.error.URLError, TimeoutError, OSError):
        raise SlackAppError("slack_unavailable", ["Slack could not be reached"]) from None


def failure(method, answer, refused_kind="credential_rejected"):
    """Return the SlackAppError for an answer from Slack that is not ok.

    `answer` is Slack's JSON answer. It may also be what Slack's GitHub Action
    reports when no answer came back: an HTTP status, a rate limit, or a
    network error.
    """
    if not isinstance(answer, dict) or not answer:
        return SlackAppError("unexpected", [f"{method}: no answer from Slack"])

    code = answer.get("error")
    if not isinstance(code, str):
        status = answer.get("statusCode")
        if "retryAfter" in answer or status == 429 or (isinstance(status, int) and status >= 500):
            return SlackAppError("slack_unavailable", [f"{method}: Slack is not answering"])
        if "errno" in answer or "syscall" in answer or isinstance(answer.get("code"), str):
            return SlackAppError("slack_unavailable", [f"{method}: Slack could not be reached"])
        return SlackAppError("unexpected", [f"{method}: an answer that is not understood"])

    if code == "invalid_manifest":
        details = [
            f"Slack: {problem.get('pointer', '/')}: {problem.get('message', '')}"
            for problem in answer.get("errors", [])
            if isinstance(problem, dict)
        ]
        return SlackAppError("invalid_definition", details or ["Slack: invalid_manifest"])
    if code in UNAVAILABLE:
        return SlackAppError("slack_unavailable", [f"{method}: {code}"])
    if code in REFUSED:
        return SlackAppError(refused_kind, [f"{method}: {code}"])
    if code == "app_not_found":
        return SlackAppError("app_gone", [f"{method}: {code}"])
    return SlackAppError("unexpected", [f"{method}: Slack answered {code}"])


class SlackApi:
    """`transport` takes (url, headers, body) and returns (status, headers, body)."""

    def __init__(self, transport=_http):
        self._transport = transport

    def _call(self, method, token, params, refused_kind):
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = urllib.parse.urlencode(params).encode()
        status, response_headers, raw = self._transport(API + method, headers, body)

        if status == 429 or status >= 500:
            raise SlackAppError("slack_unavailable", [f"{method}: HTTP {status}"])
        try:
            answer = json.loads(raw)
        except (ValueError, TypeError):
            raise SlackAppError("unexpected", [f"{method}: HTTP {status}, not JSON"]) from None
        if not isinstance(answer, dict):
            raise SlackAppError("unexpected", [f"{method}: HTTP {status}, not a JSON object"])
        if answer.get("ok"):
            return answer, response_headers
        raise failure(method, answer, refused_kind)

    def validate(self, token, manifest_json, app_id=None):
        params = {"manifest": manifest_json}
        if app_id:
            params["app_id"] = app_id
        self._call("apps.manifest.validate", token, params, "credential_rejected")

    def export(self, token, app_id):
        """Return the app's current manifest. Raises app_gone when Slack does not know it."""
        answer, _ = self._call(
            "apps.manifest.export", token, {"app_id": app_id}, "credential_rejected"
        )
        manifest = answer.get("manifest")
        return manifest if isinstance(manifest, dict) else {}

    def update(self, token, app_id, manifest_json):
        answer, _ = self._call(
            "apps.manifest.update", token, {"app_id": app_id, "manifest": manifest_json},
            "credential_rejected",
        )
        return answer

    def create(self, token, manifest_json):
        answer, _ = self._call(
            "apps.manifest.create", token, {"manifest": manifest_json}, "credential_rejected"
        )
        return answer

    def auth_test_scopes(self, bot_token):
        """Return the set of scopes the bot token holds."""
        _, headers = self._call("auth.test", bot_token, {}, "bot_token_rejected")
        scopes = headers.get("x-oauth-scopes")
        if scopes is None:
            raise SlackAppError(
                "unexpected", ["auth.test: Slack did not say which scopes the token holds"]
            )
        return {scope.strip() for scope in scopes.split(",") if scope.strip()}
