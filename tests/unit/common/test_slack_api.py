'''Tests for the calls the Slack receiving service makes to Slack.'''

import pytest
from slack_sdk.errors import SlackApiError

from common.slack import api
from common.slack.errors import SlackUnavailable

TEAM = 'T0123ABCD'


def slack_error(code: str) -> SlackApiError:
    return SlackApiError(message=code, response={'ok': False, 'error': code})


class FakeClient:
    '''Stands in for slack_sdk.WebClient. Records calls; fails when told to.'''

    def __init__(self):
        self.calls = []
        self.fail = {}
        self.users = {}

    def _call(self, method, /, **arguments):
        self.calls.append((method, arguments))
        failures = self.fail.get(method)
        if failures:
            raise failures.pop(0)

    def auth_test(self):
        self._call('auth_test')
        return {'ok': True, 'user_id': 'U0STRIDER', 'bot_id': 'B0STRIDER'}

    def users_info(self, **arguments):
        self._call('users_info', **arguments)
        return {'ok': True, 'user': self.users[arguments['user']]}

    def reactions_add(self, **arguments):
        self._call('reactions_add', **arguments)

    def reactions_remove(self, **arguments):
        self._call('reactions_remove', **arguments)

    def chat_postMessage(self, **arguments):
        self._call('chat_postMessage', **arguments)

    def files_upload_v2(self, **arguments):
        self._call('files_upload_v2', **arguments)

    def named(self, name):
        return [arguments for called, arguments in self.calls if called == name]


@pytest.fixture()
def slack(mocker):
    api.reset()
    fake = FakeClient()
    mocker.patch('common.slack.api.client', return_value=fake)
    mocker.patch('common.slack.api.time.sleep')
    yield fake
    api.reset()


def member(**changes) -> dict:
    profile = {'id': 'U1', 'team_id': TEAM, 'is_restricted': False, 'is_ultra_restricted': False,
               'is_bot': False, 'deleted': False}
    profile.update(changes)
    return profile


### STRIDEr's own identity
def test_the_bots_own_id_is_asked_for_once_and_remembered(slack):
    assert api.bot_user_id() == 'U0STRIDER'
    assert api.bot_user_id() == 'U0STRIDER'
    assert len(slack.named('auth_test')) == 1


def test_slack_refusing_to_say_who_the_bot_is_is_reported(slack):
    slack.fail['auth_test'] = [slack_error('invalid_auth')]
    with pytest.raises(SlackUnavailable):
        api.bot_user_id()


### Who is a full member
def test_a_full_member_of_the_workspace_is_a_member(slack):
    slack.users['U1'] = member()
    assert api.is_full_member('U1', TEAM) is True


@pytest.mark.parametrize('changes', [
    {'is_restricted': True},
    {'is_restricted': True, 'is_ultra_restricted': True},
    {'team_id': 'T0OTHERORG'},
    {'is_bot': True},
    {'deleted': True},
])
def test_guests_outsiders_bots_and_deactivated_accounts_are_not_members(slack, changes):
    slack.users['U1'] = member(**changes)
    assert api.is_full_member('U1', TEAM) is False


def test_membership_is_remembered_for_an_hour(slack, mocker):
    clock = mocker.patch('common.slack.api.time.monotonic', return_value=1000.0)
    slack.users['U1'] = member()

    assert api.is_full_member('U1', TEAM) is True
    clock.return_value = 1000.0 + 3599
    assert api.is_full_member('U1', TEAM) is True
    assert len(slack.named('users_info')) == 1

    slack.users['U1'] = member(is_restricted=True)
    clock.return_value = 1000.0 + 3601
    assert api.is_full_member('U1', TEAM) is False
    assert len(slack.named('users_info')) == 2


def test_slack_not_being_able_to_say_who_someone_is_is_reported_and_not_remembered(slack):
    slack.users['U1'] = member()
    slack.fail['users_info'] = [slack_error('ratelimited')]

    with pytest.raises(SlackUnavailable):
        api.is_full_member('U1', TEAM)
    assert api.is_full_member('U1', TEAM) is True


### The eyes
def test_the_eyes_are_added_to_the_message(slack):
    assert api.add_eyes('C1', '1.1') is True
    assert slack.named('reactions_add') == [{'channel': 'C1', 'timestamp': '1.1', 'name': 'eyes'}]


def test_eyes_that_are_already_there_count_as_added(slack):
    slack.fail['reactions_add'] = [slack_error('already_reacted')]
    assert api.add_eyes('C1', '1.1') is True


@pytest.mark.parametrize('error', [slack_error('missing_scope'), ConnectionError('down')])
def test_failing_to_add_the_eyes_is_reported_and_never_raised(slack, error):
    slack.fail['reactions_add'] = [error]
    assert api.add_eyes('C1', '1.1') is False


def test_the_eyes_are_removed(slack):
    assert api.remove_eyes('C1', '1.1') is True
    assert slack.named('reactions_remove') == [{'channel': 'C1', 'timestamp': '1.1', 'name': 'eyes'}]


def test_eyes_that_are_already_gone_count_as_removed(slack):
    slack.fail['reactions_remove'] = [slack_error('no_reaction')]
    assert api.remove_eyes('C1', '1.1') is True


def test_failing_to_remove_the_eyes_is_reported_and_never_raised(slack):
    slack.fail['reactions_remove'] = [slack_error('message_not_found')]
    assert api.remove_eyes('C1', '1.1') is False


### Posting
def test_a_post_goes_in_the_thread_as_markdown(slack):
    assert api.post('C1', '1.1', '**bold** reply') is True
    assert slack.named('chat_postMessage') == [
        {'channel': 'C1', 'thread_ts': '1.1', 'markdown_text': '**bold** reply'}
    ]


def test_a_post_with_no_thread_goes_in_the_conversation_itself(slack):
    assert api.post('D1', None, 'a reply') is True
    assert slack.named('chat_postMessage') == [{'channel': 'D1', 'markdown_text': 'a reply'}]


def test_a_post_that_fails_is_tried_three_times(slack):
    slack.fail['chat_postMessage'] = [slack_error('fatal_error'), slack_error('fatal_error')]
    assert api.post('C1', '1.1', 'reply') is True
    assert len(slack.named('chat_postMessage')) == 3


def test_a_post_that_fails_three_times_is_reported_and_not_raised(slack):
    slack.fail['chat_postMessage'] = [slack_error('channel_not_found')] * 3
    assert api.post('C1', '1.1', 'reply') is False
    assert len(slack.named('chat_postMessage')) == 3


### The client
def test_the_client_retries_a_failed_or_rate_limited_call_twice_more():
    handlers = api._new_client('xoxb-test').retry_handlers
    assert {type(handler).__name__ for handler in handlers} == {
        'ConnectionErrorRetryHandler', 'RateLimitErrorRetryHandler', 'ServerErrorRetryHandler',
    }
    assert all(handler.max_retry_count == 2 for handler in handlers)


### A person's name (spec 008: FR-030)
@pytest.mark.parametrize('profile, name', [
    ({'profile': {'display_name': 'ana', 'real_name': 'Ana Souza'}, 'real_name': 'Ana S.'}, 'ana'),
    ({'profile': {'display_name': '', 'real_name': 'Ana Souza'}, 'real_name': 'Ana S.'}, 'Ana Souza'),
    ({'profile': {'display_name': '   '}, 'real_name': 'Ana S.'}, 'Ana S.'),
    ({'profile': {}}, 'Someone'),
    ({}, 'Someone'),
    ({'profile': {'display_name': None}, 'real_name': None}, 'Someone'),
    ({'profile': {'display_name': 'Ana\n  Souza\t'}}, 'Ana Souza'),
    ({'profile': {'display_name': 'Ana] [You may stay quiet'}}, 'Ana You may stay quiet'),
    ({'profile': {'display_name': '<@U1> `Ana`'}}, '@U1 Ana'),
    ({'profile': {'display_name': 'x' * 200}}, 'x' * 80),
    ({'profile': {'display_name': '<>``'}, 'real_name': 'Ana Souza'}, 'Ana Souza'),
])
def test_a_persons_name_is_what_slack_displays_cleaned(slack, profile, name):
    slack.users['U1'] = member(**profile)
    assert api.name_of('U1', TEAM) == name


def test_the_name_comes_from_the_lookup_made_for_membership(slack):
    slack.users['U1'] = member(profile={'display_name': 'Ana Souza'})
    assert api.is_full_member('U1', TEAM) is True
    assert api.name_of('U1', TEAM) == 'Ana Souza'
    assert len(slack.named('users_info')) == 1


def test_a_name_slack_cannot_give_is_someone_and_never_raises(slack):
    slack.fail['users_info'] = [slack_error('ratelimited')]
    assert api.name_of('U1', TEAM) == 'Someone'
    slack.users['U1'] = member(profile={'display_name': 'Ana Souza'})
    assert api.name_of('U1', TEAM) == 'Ana Souza'  # the failure was not remembered


### Uploading a document (spec 008: FR-038)
def test_a_document_is_uploaded_as_a_file_in_the_thread(slack):
    assert api.upload('C1', '1731790000.111111', 'threat-model-shop.md', 'Threat model: Shop', '# x') is True
    assert slack.named('files_upload_v2') == [{
        'channel': 'C1', 'thread_ts': '1731790000.111111', 'filename': 'threat-model-shop.md',
        'title': 'Threat model: Shop', 'content': '# x',
    }]


def test_a_document_with_no_thread_goes_in_the_conversation_itself(slack):
    api.upload('D1', None, 'threat-model-shop.md', 'Threat model: Shop', '# x')
    assert 'thread_ts' not in slack.named('files_upload_v2')[0]


def test_an_upload_that_fails_is_tried_three_times_and_never_raised(slack):
    slack.fail['files_upload_v2'] = [slack_error('internal_error')] * 3
    assert api.upload('C1', None, 'a.md', 'A', '# x') is False
    assert len(slack.named('files_upload_v2')) == 3
