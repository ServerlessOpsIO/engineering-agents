'''Checks that a request came from Slack.

Slack signs every request with the app's signing secret. See
https://docs.slack.dev/authentication/verifying-requests-from-slack
'''

import hashlib
import hmac
from typing import Optional

# A request whose time of sending is further than this from now is refused,
# so that a captured request cannot be sent again later.
MAX_AGE_SECONDS = 300


def verify(
    signing_secret: str,
    timestamp: Optional[str],
    signature: Optional[str],
    body: str,
    now: float,
) -> bool:
    '''Say whether the signature proves Slack sent this body at this time.

    body must be the request body exactly as it was received, before it is
    parsed: the signature is computed over its bytes.
    '''
    if not timestamp or not signature:
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs(now - sent_at) > MAX_AGE_SECONDS:
        return False

    base = f'v0:{timestamp}:{body}'.encode('utf-8')
    expected = 'v0=' + hmac.new(signing_secret.encode('utf-8'), base, hashlib.sha256).hexdigest()
    # compare_digest takes the same time however much of the signature is right.
    return hmac.compare_digest(expected.encode('utf-8'), signature.encode('utf-8'))
