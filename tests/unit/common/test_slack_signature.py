'''Tests for the check that a request came from Slack.'''

import hashlib
import hmac

import pytest

from common.slack.signature import verify

SECRET = 'test-signing-secret'
NOW = 1731790000
BODY = '{"type":"event_callback","event":{"type":"app_mention"}}'


def sign(body: str, timestamp, secret: str = SECRET) -> str:
    base = f'v0:{timestamp}:{body}'.encode('utf-8')
    return 'v0=' + hmac.new(secret.encode('utf-8'), base, hashlib.sha256).hexdigest()


def test_a_correct_signature_passes():
    assert verify(SECRET, str(NOW), sign(BODY, NOW), BODY, NOW)


def test_slacks_documented_example_passes():
    # The worked example on Slack's "Verifying requests from Slack" page.
    secret = '8f742231b10e8888abcd99yyyzzz85a5'
    timestamp = '1531420618'
    body = (
        'token=xyzz0WbapA4vBCDEFasx0q6G&team_id=T1DC2JH3J&team_domain=testteamnow'
        '&channel_id=G8PSS9T3V&channel_name=foobar&user_id=U2CERLKJA&user_name=roadrunner'
        '&command=%2Fwebhook-collect&text=&response_url=https%3A%2F%2Fhooks.slack.com'
        '%2Fcommands%2FT1DC2JH3J%2F397700885554%2F96rGlfmibIGlgcZRskXaIFfN'
        '&trigger_id=398738663015.47445629121.803a0bc887a14d10d2c447fce8b6703c'
    )
    signature = 'v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10bd27519666489c69b503'
    assert verify(secret, timestamp, signature, body, int(timestamp))


@pytest.mark.parametrize('timestamp, signature', [
    (None, sign(BODY, NOW)),
    ('', sign(BODY, NOW)),
    (str(NOW), None),
    (str(NOW), ''),
])
def test_a_missing_timestamp_or_signature_fails(timestamp, signature):
    assert not verify(SECRET, timestamp, signature, BODY, NOW)


def test_a_timestamp_that_is_not_a_whole_number_fails():
    assert not verify(SECRET, 'yesterday', sign(BODY, 'yesterday'), BODY, NOW)
    assert not verify(SECRET, '1731790000.5', sign(BODY, '1731790000.5'), BODY, NOW)


def test_a_wrong_signature_fails():
    assert not verify(SECRET, str(NOW), 'v0=' + '0' * 64, BODY, NOW)


def test_a_signature_made_with_another_secret_fails():
    assert not verify(SECRET, str(NOW), sign(BODY, NOW, secret='another'), BODY, NOW)


def test_a_signature_for_a_different_body_fails():
    assert not verify(SECRET, str(NOW), sign(BODY, NOW), BODY + ' ', NOW)


def test_the_body_is_used_exactly_as_given():
    # The same JSON written with different spacing is a different body.
    respaced = BODY.replace(':', ': ')
    assert not verify(SECRET, str(NOW), sign(BODY, NOW), respaced, NOW)
    assert verify(SECRET, str(NOW), sign(respaced, NOW), respaced, NOW)


@pytest.mark.parametrize('age', [300, -300, 0])
def test_a_timestamp_within_five_minutes_passes(age):
    timestamp = NOW - age
    assert verify(SECRET, str(timestamp), sign(BODY, timestamp), BODY, NOW)


@pytest.mark.parametrize('age', [301, -301, 86400])
def test_a_timestamp_more_than_five_minutes_away_fails(age):
    timestamp = NOW - age
    assert not verify(SECRET, str(timestamp), sign(BODY, timestamp), BODY, NOW)


def test_a_signature_with_characters_outside_ascii_fails_without_an_error():
    assert not verify(SECRET, str(NOW), 'v0=café', BODY, NOW)
