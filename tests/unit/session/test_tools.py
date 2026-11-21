"""Unit tests for the tools the model calls (contracts/session-tools.md)."""

import json
import logging

import pytest

from session import record as rec
from session import tools
from session.tools import Turn


class FakeState:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        json.dumps(value)
        self.values[key] = value


@pytest.fixture
def state():
    return FakeState()


def turn_for(state, speaker="Ana Souza", kind=tools.DIRECT_MESSAGE, ends=None):
    return Turn(state, speaker, kind, ends, today="2026-11-22")


def next_message(state, speaker="Ana Souza", **kwargs):
    """Move to the next message the way main.py does, and return its Turn."""
    session = rec.load(state)
    session.next_turn()
    session.add_person(speaker)
    rec.save(state, session)
    return turn_for(state, speaker, **kwargs)


@pytest.fixture
def turn(state):
    t = turn_for(state)
    t.start_session("Login service")
    return t


@pytest.fixture
def modelled(turn, state):
    """A session with a small system, in the threats stage."""
    turn.complete_stage()
    turn.add_element("component", "API")
    turn.add_element("data_store", "Users table")
    turn.add_data_flow("C1", "DS1", "user rows")
    turn.complete_stage()
    return turn


def finish(state):
    t = next_message(state)
    t.request_change("finish")
    t = next_message(state)
    return t, t.resolve_change(True)


# --- which tools are offered --------------------------------------------------


def test_there_are_twenty_five_tools():
    assert len(tools.ALL_TOOLS) == 25 == len(set(tools.ALL_TOOLS))


def test_with_no_session_only_starting_and_reading_are_offered():
    assert tools.tools_for(None) == ("start_session", "list_repository_files", "read_repository_file")


@pytest.mark.parametrize("stage, expected", [
    ("scope", {"add_scope_item", "remove_item"}),
    ("system", {"add_element", "add_data_flow", "add_trust_boundary", "change_element",
                "description_complete", "remove_item"}),
    ("threats", {"add_threat", "none_found", "remove_item"}),
    ("rating", {"rate_threat", "add_threat"}),
    ("mitigations", {"add_mitigation", "decide_threat", "rate_threat", "add_threat", "remove_item"}),
    ("model", set()),
])
def test_in_a_session_the_stage_decides_what_is_offered(turn, state, stage, expected):
    turn.go_to_stage(stage)
    offered = set(tools.tools_for(rec.load(state)))
    assert "start_session" not in offered
    assert set(tools.SESSION_TOOLS) <= offered and set(tools.REPOSITORY_TOOLS) <= offered
    assert offered - set(tools.SESSION_TOOLS) - set(tools.REPOSITORY_TOOLS) == expected


def test_never_more_than_eighteen_are_offered(turn, state):
    counts = [len(tools.tools_for(None))]
    for stage in rec.STAGES:
        turn.go_to_stage(stage)
        counts.append(len(tools.tools_for(rec.load(state))))
    finish(state)
    counts.append(len(tools.tools_for(rec.load(state))))
    assert max(counts) == 18


@pytest.mark.parametrize("action", ["finish", "abandon"])
def test_after_the_end_the_model_can_still_be_changed_and_posted(turn, state, action):
    t = next_message(state)
    t.request_change(action)
    next_message(state).resolve_change(True)
    offered = set(tools.tools_for(rec.load(state)))
    assert {"start_session", "write_model", "add_open_question", "add_threat", "remove_item"} <= offered
    assert not {"give_hint", "add_note", "request_change", "complete_stage"} & offered


def test_make_tools_wraps_each_tool_with_a_short_description(turn):
    made = tools.make_tools(turn)
    assert set(made) == set(tools.ALL_TOOLS) - set(tools.REPOSITORY_TOOLS)
    for name, wrapped in made.items():
        spec = wrapped.tool_spec
        assert spec["name"] == name
        assert 0 < len(spec["description"].split()) <= 50
        assert "session" not in spec["inputSchema"]["json"]["properties"]


# --- starting -----------------------------------------------------------------


def test_starting_adds_the_speaker_and_returns_the_opening(state):
    said = turn_for(state).start_session("Login service")
    session = rec.load(state)
    assert session["participants"] == ["Ana Souza"]
    assert session["startedOn"] == "2026-11-22"
    assert "six stages" in said and "participants do the work" in said and "keep notes" in said
    assert "stay quiet" not in said and "full members" not in said


def test_in_a_channel_thread_the_opening_says_more(state):
    said = turn_for(state, kind=tools.CHANNEL_THREAD, ends="2026-11-29T10:00:00Z").start_session("Shop")
    assert "stay quiet" in said and "mention always gets a reply" in said
    assert "full members" in said
    assert "2026-11-29T10:00:00Z" in said


def test_a_second_start_is_refused_while_one_is_in_progress(turn, state):
    said = turn.start_session("Another")
    assert said.startswith("Not done.") and "continue it or abandon it" in said
    assert rec.load(state)["system"] == "Login service"


def test_starting_after_an_ended_session_is_refused_once_then_replaces_it(turn, state):
    finish(state)
    t = next_message(state)
    assert "replaces it" in t.start_session("Shop")
    assert "replaces it" in t.start_session("Shop")  # same message: still refused
    assert rec.load(state)["system"] == "Login service"
    assert "Session started" in next_message(state).start_session("Shop")
    assert rec.load(state)["system"] == "Shop" and rec.load(state).in_progress


def test_starting_empties_the_files_read_and_keeps_named_repositories(state):
    rec.save_repositories(state, [{"name": "shop", "listed": True, "filesRead": ["README.md"]}])
    turn_for(state).start_session("Shop")
    assert rec.load_repositories(state) == [{"name": "shop", "listed": True, "filesRead": []}]


# --- recording, and reading back ----------------------------------------------


def test_each_recording_tool_answers_with_the_entry_and_its_identifier(modelled):
    assert "Recorded as T1: tampering on C1, jobs altered." in modelled.add_threat("C1", "tampering", "jobs altered")
    modelled.go_to_stage("rating")
    said = modelled.rate_threat("T1", "high", "anyone can", "medium", "some data")
    assert "likelihood high, impact medium" in said and "severity that follows from the table is high" in said
    modelled.go_to_stage("mitigations")
    assert "Recorded as M1: sign jobs, addressing T1, owner none named." in modelled.add_mitigation("sign jobs", ["T1"])
    said = modelled.decide_threat("T1", "mitigate", ["Ana Souza"])
    assert "Recorded as T1: mitigate, decided by Ana Souza" in said
    assert "ask once who is responsible" in said
    assert "ask once" not in modelled.decide_threat("T1", "mitigate", ["Ana Souza"])


def test_recording_tools_for_scope_and_system_read_back(turn):
    assert "Recorded as S1, included: the API." in turn.add_scope_item("included", "the API")
    turn.complete_stage()
    assert "Recorded as C1, a component: API." in turn.add_element("component", "API")
    assert "Recorded as EP1, a external party: Browser." in turn.add_element("external_party", "Browser")
    assert "Recorded as F1, a data flow from EP1 to C1: credentials." in turn.add_data_flow("EP1", "C1", "credentials")
    assert "Recorded as TB1, a trust boundary: Internal, holding C1." in turn.add_trust_boundary("Internal", ["C1"])
    assert "Recorded as Q1, an open question" in turn.add_open_question("who rotates keys?")


@pytest.mark.parametrize("call", [
    lambda t: t.add_element("gateway", "x"),
    lambda t: t.add_data_flow("C1", "C9", "x"),
    lambda t: t.add_threat("C9", "tampering", "x"),
    lambda t: t.add_threat("C1", "phishing", "x"),
    lambda t: t.rate_threat("T9", "high", "a", "low", "b"),
    lambda t: t.add_mitigation("x", []),
    lambda t: t.decide_threat("T9", "mitigate", ["Ana Souza"]),
    lambda t: t.remove_item("C9"),
    lambda t: t.go_to_stage("coffee"),
    lambda t: t.request_change("pause"),
    lambda t: t.resolve_change(True),
    lambda t: t.hint_taken_up("H9"),
    lambda t: t.add_note("gossip", "x"),
])
def test_a_refused_call_answers_with_a_sentence_and_does_not_raise(modelled, call):
    said = call(modelled)
    assert said.startswith("Not done.") and len(said) > len("Not done. ")


def test_a_tool_with_no_session_is_refused(state):
    assert turn_for(state).add_threat("C1", "tampering", "x").startswith("Not done. There is no session.")


def test_a_decision_by_someone_not_in_the_session_is_refused(modelled):
    modelled.add_threat("C1", "tampering", "x")
    assert "Not in this session: Carla" in modelled.decide_threat("T1", "mitigate", ["Carla"])


def test_removing_says_what_went_with_it(modelled):
    said = modelled.remove_item("C1")
    assert said.startswith("Removed C1.") and "F1" in said and said.endswith("Say so.")


# --- stages -------------------------------------------------------------------


def test_complete_stage_is_never_refused_and_names_the_next(turn):
    said = turn.complete_stage()
    assert "scope stage is complete" in said and "Now in the system stage" in said


def test_leaving_the_threats_stage_lists_what_was_not_looked_at(modelled, state):
    modelled.add_threat("C1", "spoofing", "x")
    modelled.none_found("C1", "tampering")
    said = modelled.complete_stage()
    assert "Not looked at:" in said and "Not considered" in said and "name no threat" in said
    assert "C1: repudiation, information disclosure" in said
    assert "F1: tampering" in said
    assert rec.load(state)["stage"] == "rating"


def test_the_last_stage_asks_whether_to_finish(turn):
    turn.go_to_stage("model")
    assert "Ask whether the participants want to finish" in turn.complete_stage()


def _hold(state, turn):
    rec.save_repositories(state, [{"name": "shop", "listed": True, "filesRead": ["README.md"]}])
    session = rec.load(state)
    session.add_finding("not_mentioned", "shop", "README.md", "there is a cache", ["README.md"])
    rec.save(state, session)


def test_description_complete_returns_every_held_finding_at_once(turn, state):
    turn.complete_stage()
    _hold(state, turn)
    said = turn.description_complete()
    assert "shop/README.md: there is a cache" in said and "naming each file" in said
    assert "Nothing from a repository was being held back." in turn.description_complete()


def test_completing_the_system_stage_releases_findings_and_a_skip_does_not(turn, state):
    turn.complete_stage()
    _hold(state, turn)
    assert "shop/README.md: there is a cache" in turn.complete_stage()

    other = FakeState()
    t = turn_for(other)
    t.start_session("Shop")
    t.complete_stage()
    _hold(other, t)
    assert "cache" not in t.request_change("skip_stage")
    assert rec.load(other)["findings"][0]["reported"] is False


# --- hints and notes ----------------------------------------------------------


def test_a_second_hint_for_an_element_in_a_stage_is_refused(modelled):
    assert "DO NOT name the threat" in modelled.give_hint("what the API trusts", "C1")
    said = modelled.give_hint("something else", "C1")
    assert said.startswith("Not done.") and "add_note" in said and "say nothing" in said
    assert modelled.add_note("not_raised", "something else", element="C1") == "Noted. Do not mention it."


# --- skipping, finishing, abandoning, and the documents -----------------------


def test_one_participant_skips_at_once(turn, state):
    assert "Skipped. Now in the system stage" in turn.request_change("skip_stage")
    assert rec.load(state)["stages"]["scope"] == "skipped"


def test_several_participants_skip_after_an_announcement(turn, state):
    t = next_message(state, "Ben Okafor")
    assert "about to be skipped" in t.request_change("skip_stage")
    assert t.resolve_change(True).startswith("Not done.")
    assert "Skipped." in next_message(state).resolve_change(True)


def test_a_finish_is_announced_then_attaches_both_documents(turn, state):
    t = next_message(state)
    said = t.request_change("finish")
    assert "about to be posted" in said and "marked" in said
    assert t.documents == []
    assert t.resolve_change(True).startswith("Not done.")
    t, said = next_message(state), None
    said = t.resolve_change(True)
    assert "finished" in said and "Do not write them out" in said
    assert [d["filename"] for d in t.documents] == [
        "threat-model-login-service.md", "facilitator-notes-login-service.md",
    ]
    assert t.documents[0]["title"] == "Threat model: Login service"
    assert "> Status: **Finished**." in t.documents[0]["markdown"]
    assert t.documents[1]["markdown"].startswith("# Facilitator's notes: Login service")
    assert rec.load(state)["status"] == "finished"


def test_an_abandon_attaches_both_documents_with_unfinished_stages_marked(turn, state):
    t = next_message(state)
    t.request_change("abandon")
    t = next_message(state)
    assert "abandoned" in t.resolve_change(True)
    assert len(t.documents) == 2
    assert "> Status: **Abandoned**." in t.documents[0]["markdown"]
    assert "> Not finished: Scope." in t.documents[0]["markdown"]
    session = rec.load(state)
    assert session["status"] == "abandoned" and session["notesPostedOnTurn"] == session["turn"]


def test_an_objection_drops_the_request(turn, state):
    next_message(state).request_change("finish")
    t = next_message(state)
    assert "Dropped." in t.resolve_change(False)
    assert t.documents == []
    assert next_message(state).resolve_change(True).startswith("Not done. Nothing is pending.")


def test_write_model_attaches_the_model_alone_while_in_progress(modelled):
    said = modelled.write_model()
    assert "as it stands" in said and "Do not write it out" in said
    assert [d["filename"] for d in modelled.documents] == ["threat-model-login-service.md"]
    assert "> Status: **In progress**." in modelled.documents[0]["markdown"]
    modelled.write_model()
    assert len(modelled.documents) == 1  # asked twice in one reply: still one file


def test_write_model_attaches_both_once_the_session_has_ended(turn, state):
    finish(state)
    t = next_message(state)
    t.add_threat("C1", "tampering", "x")  # refused: no such element; nothing changes
    assert "facilitator's notes are attached" in t.write_model()
    assert len(t.documents) == 2


def test_a_change_after_the_notes_is_marked_in_the_model_posted_again(modelled, state):
    modelled.add_threat("C1", "tampering", "before")
    finish(state)
    t = next_message(state, "Carla Mendes")
    t.add_threat("C1", "spoofing", "after")
    t.write_model()
    text = t.documents[0]["markdown"]
    assert "| T2† |" in text and "| T1 |" in text
    assert "- **Joined after the session**: Carla Mendes" in text


# --- faults -------------------------------------------------------------------


def test_a_fault_inside_a_tool_answers_with_a_sentence_and_logs_only_its_type(modelled, monkeypatch, caplog):
    def explode(*args, **kwargs):
        raise RuntimeError("zebra crossing detail")

    monkeypatch.setattr(rec.Record, "add_threat", explode)
    with caplog.at_level(logging.ERROR, logger="agent"):
        logging.getLogger("agent").propagate = True
        said = modelled.add_threat("C1", "tampering", "giraffe enclosure")
        logging.getLogger("agent").propagate = False
    assert said == tools.SOMETHING_WENT_WRONG
    assert "RuntimeError" in caplog.text
    assert "zebra" not in caplog.text and "giraffe" not in caplog.text


def test_tool_calls_are_counted(turn):
    before = turn.tool_calls
    turn.add_scope_item("included", "x")
    turn.add_scope_item("bogus", "x")
    assert turn.tool_calls == before + 2


# --- pace: back, skip, early model (US6) ---------------------------------------


def test_a_skipped_stage_is_marked_in_the_model(turn):
    turn.request_change("skip_stage")
    turn.write_model()
    text = turn.documents[0]["markdown"]
    assert "> Skipped: Scope." in text


def test_going_back_and_removing_an_element_changes_the_coverage(modelled):
    modelled.add_threat("C1", "spoofing", "x")
    modelled.write_model()
    assert "| DS1 (Users table) |" in modelled.documents[0]["markdown"]
    assert "Now in the system stage" in modelled.go_to_stage("system")
    modelled.remove_item("DS1")
    modelled.go_to_stage("threats")
    modelled.write_model()
    text = modelled.documents[0]["markdown"]
    assert "DS1" not in text and "| C1 (API) | T1 |" in text


def test_asking_for_the_model_twice_gives_the_current_state_each_time(modelled, state):
    modelled.write_model()
    assert "No threats recorded." in modelled.documents[0]["markdown"]
    later = next_message(state)
    later.add_threat("C1", "tampering", "jobs altered")
    later.write_model()
    assert "jobs altered" in later.documents[0]["markdown"]
    assert len(later.documents) == 1
