"""Test setup that must run before the agent module is imported."""

import os

# main.py refuses to start without MODEL_ID. The tests replace the model with a
# fake, so any value works here.
os.environ.setdefault("MODEL_ID", "test.provider.model")
