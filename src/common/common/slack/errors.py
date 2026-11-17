'''Errors the Slack receiving service raises about Slack.'''


class SlackUnavailable(Exception):
    '''Slack could not be asked, or would not answer, after the allowed tries.'''
