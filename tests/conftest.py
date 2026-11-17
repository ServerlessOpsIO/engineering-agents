"""Test setup that must run before the agent module is imported."""

import os

# main.py refuses to start without MODEL_ID. The tests replace the model with a
# fake, so any value works here.
os.environ.setdefault("MODEL_ID", "test.provider.model")

from collections import namedtuple

import pytest


@pytest.fixture()
def lambda_function_context():
    """Return a factory for the context object Lambda passes to a handler."""
    def _factory(function_name: str, object_name: str = 'LambdaContext'):
        context_info = {
            'aws_request_id': '00000000-0000-0000-0000-000000000000',
            'function_name': function_name,
            'invoked_function_arn': f'arn:aws:lambda:us-east-1:012345678910:function:{function_name}',
            'memory_limit_in_mb': 128,
        }
        Context = namedtuple(object_name, context_info.keys())
        return Context(*context_info.values())
    return _factory
