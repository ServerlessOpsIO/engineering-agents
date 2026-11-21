"""Unit tests for the session record: the rules of data-model.md that code keeps."""

import json

import pytest

from session import record as rec
from session.record import Record, Refused


class FakeState:
    """Stands in for the agent's key-value state."""

    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        json.dumps(value)  # Only JSON may be kept.
        self.values[key] = value


@pytest.fixture
def session():
    return Record.start("stride-threat-model", "Login service", "Ana Souza", "2026-11-21")


@pytest.fixture
def system(session):
    """A session with two components, a store, an outsider and a flow."""
    session.add_element("component", "API")
    session.add_element("component", "Worker")
    session.add_element("data_store", "Users table")
    session.add_element("external_party", "Browser")
    session.add_data_flow("C1", "C2", "jobs")
    return session


# --- starting -----------------------------------------------------------------


def test_a_new_session_starts_in_scope_with_its_starter_as_a_participant(session):
    assert session["stage"] == "scope"
    assert session["stages"]["scope"] == "in_progress"
    assert session["stages"]["system"] == "not_started"
    assert session["participants"] == ["Ana Souza"]
    assert session.in_progress


def test_a_record_survives_a_round_trip_through_json(system):
    again = Record.from_dict(json.loads(json.dumps(system.to_dict())))
    assert again.to_dict() == system.to_dict()


@pytest.mark.parametrize("damage", [
    lambda d: d.pop("threats"),
    lambda d: d.update(status="paused"),
    lambda d: d.update(stage="coffee"),
    lambda d: d["stages"].pop("model"),
    lambda d: d.update(turn="3"),
])
def test_a_record_that_does_not_validate_is_no_session(session, damage):
    data = session.to_dict()
    damage(data)
    state = FakeState()
    state.set(rec.KEY_SESSION, data)
    assert rec.load(state) is None


# --- identifiers --------------------------------------------------------------


def test_identifiers_are_given_by_kind_and_never_reused(system):
    assert [e["id"] for e in system["elements"]] == ["C1", "C2", "DS1", "EP1", "F1"]
    assert system.add_boundary("Internal", ["C1", "C2"])["id"] == "TB1"
    assert system.add_scope_item("included", "the API")["id"] == "S1"
    assert system.add_threat("C1", "spoofing", "forged token")["id"] == "T1"
    assert system.add_mitigation("sign tokens", ["T1"])["id"] == "M1"
    assert system.add_open_question("who rotates keys?")["id"] == "Q1"
    system.remove("C2")
    assert system.add_element("component", "Scheduler")["id"] == "C3"


# --- the system ---------------------------------------------------------------


def test_a_data_flow_needs_two_ends_that_exist_and_are_not_flows(system):
    with pytest.raises(Refused):
        system.add_data_flow("C1", "C9", "x")
    with pytest.raises(Refused):
        system.add_data_flow("F1", "C1", "x")


def test_removing_an_element_takes_its_flows_none_found_and_boundary_place(system):
    system.add_boundary("Internal", ["C1", "C2"])
    system.none_found("C2", "spoofing")
    system.none_found("F1", "tampering")
    said = system.remove("C2")
    assert "F1" in said
    assert [e["id"] for e in system["elements"]] == ["C1", "DS1", "EP1"]
    assert system["noneFound"] == []
    assert system["boundaries"][0]["inside"] == ["C1"]


def test_an_element_named_by_a_threat_cannot_be_removed(system):
    system.add_threat("F1", "tampering", "jobs altered")
    with pytest.raises(Refused, match="T1"):
        system.remove("C1")


# --- threats and ratings ------------------------------------------------------


def test_adding_a_threat_removes_none_found_for_that_cell(system):
    system.none_found("C1", "spoofing")
    system.add_threat("C1", "spoofing", "forged token")
    assert system["noneFound"] == []


def test_none_found_is_refused_where_a_threat_exists(system):
    system.add_threat("C1", "spoofing", "forged token")
    with pytest.raises(Refused):
        system.none_found("C1", "spoofing")


@pytest.mark.parametrize("impact, likelihood, severity", [
    ("high", "low", "medium"), ("high", "medium", "high"), ("high", "high", "critical"),
    ("medium", "low", "low"), ("medium", "medium", "medium"), ("medium", "high", "high"),
    ("low", "low", "note"), ("low", "medium", "low"), ("low", "high", "medium"),
])
def test_severity_is_read_from_the_owasp_table(system, impact, likelihood, severity):
    system.add_threat("C1", "tampering", "x")
    assert system["threats"][0]["severity"] is None
    assert system.rate_threat("T1", likelihood, "because", impact, "because") == severity
    assert system["threats"][0]["severity"] == severity


def test_a_rating_needs_both_reasons_and_known_values(system):
    system.add_threat("C1", "tampering", "x")
    with pytest.raises(Refused):
        system.rate_threat("T1", "high", "", "low", "because")
    with pytest.raises(Refused):
        system.rate_threat("T1", "high", "because", "low", " ")
    with pytest.raises(Refused):
        system.rate_threat("T1", "severe", "because", "low", "because")


# --- decisions and mitigations ------------------------------------------------


def test_accepting_a_threat_needs_a_reason(system):
    system.add_threat("C1", "tampering", "x")
    with pytest.raises(Refused):
        system.decide_threat("T1", "accept", "", ["Ana Souza"])
    system.decide_threat("T1", "accept", "internal only", ["Ana Souza"])
    assert system["threats"][0]["decisionReason"] == "internal only"


def test_a_decision_is_made_by_people_in_the_session(system):
    system.add_threat("C1", "tampering", "x")
    with pytest.raises(Refused, match="Carla"):
        system.decide_threat("T1", "mitigate", "", ["Carla"])
    system.add_person("Ben Okafor")
    system.decide_threat("T1", "mitigate", "", ["Ana Souza", "Ben Okafor"])
    assert system["threats"][0]["decidedBy"] == ["Ana Souza", "Ben Okafor"]


def test_an_owner_is_asked_for_once(system):
    system.add_threat("C1", "tampering", "x")
    assert system.decide_threat("T1", "mitigate", "", ["Ana Souza"]) is True
    assert system.decide_threat("T1", "mitigate", "", ["Ana Souza"]) is False
    assert system.decide_threat("T1", "mitigate", "", ["Ana Souza"], "Platform team") is False
    assert system["threats"][0]["owner"] == "Platform team"


def test_a_mitigation_addresses_at_least_one_threat_that_exists(system):
    with pytest.raises(Refused):
        system.add_mitigation("sign jobs", [])
    with pytest.raises(Refused):
        system.add_mitigation("sign jobs", ["T7"])


def test_removing_a_threat_takes_it_out_of_mitigations_and_drops_an_empty_one(system):
    system.add_threat("C1", "tampering", "x")
    system.add_threat("C2", "tampering", "y")
    system.add_mitigation("sign jobs", ["T1", "T2"])
    system.add_mitigation("validate input", ["T1"])
    said = system.remove("T1")
    assert "M2" in said
    assert [(m["id"], m["threats"]) for m in system["mitigations"]] == [("M1", ["T2"])]


def test_hints_notes_and_findings_cannot_be_removed(system):
    hint = system.give_hint(None, "the admin console")
    with pytest.raises(Refused):
        system.remove(hint["id"])


# --- hints, notes and findings ------------------------------------------------


def test_one_hint_for_each_element_in_each_stage(system):
    system.go_to_stage("threats")
    system.give_hint("C1", "what the worker trusts")
    with pytest.raises(Refused, match="add_note"):
        system.give_hint("C1", "something else")
    system.give_hint("C2", "another element is fine")
    system.go_to_stage("rating")
    system.give_hint("C1", "a new stage is fine")


def test_the_scope_stage_has_one_hint_and_no_element(session):
    session.give_hint(None, "the admin console is left out")
    with pytest.raises(Refused):
        session.give_hint(None, "again")


def test_a_hint_outside_scope_names_its_element(system):
    system.go_to_stage("threats")
    with pytest.raises(Refused):
        system.give_hint(None, "x")


def test_a_finding_names_a_file_read_and_is_held_until_the_description_is_complete(system):
    with pytest.raises(Refused):
        system.add_finding("differs", "shop", "template.yaml", "there is a queue", ["README.md"])
    held = system.add_finding("differs", "shop", "README.md", "there is a queue", ["README.md"])
    assert held["reported"] is False
    assert [f["id"] for f in system.mark_description_complete()] == ["R1"]
    assert system.mark_description_complete() == []
    later = system.add_finding("not_mentioned", "shop", "README.md", "a cache", ["README.md"])
    assert later["reported"] is True


# --- coverage -----------------------------------------------------------------


def test_coverage_has_a_cell_for_each_category_by_kind(system):
    system.add_threat("C1", "spoofing", "x")
    system.none_found("C1", "tampering")
    cells = system.coverage(system.element("C1"))
    assert cells["spoofing"] == ["T1"]
    assert cells["tampering"] == "none_found"
    assert cells["repudiation"] == "not_considered"
    flow = system.coverage(system.element("F1"))
    assert flow["spoofing"] == "n/a" and flow["tampering"] == "not_considered"
    store = system.coverage(system.element("DS1"))
    assert store["repudiation"] == "not_considered" and store["elevation_of_privilege"] == "n/a"
    outsider = system.coverage(system.element("EP1"))
    assert [c for c, v in outsider.items() if v != "n/a"] == ["spoofing", "repudiation"]


def test_fifteen_pairs_of_kind_and_category_apply():
    assert sum(len(categories) for categories in rec.APPLIES.values()) == 15


# --- stages -------------------------------------------------------------------


def test_completing_a_stage_enters_the_next(session):
    done = session.complete_stage()
    assert (done["left"], done["entered"]) == ("scope", "system")
    assert session["stages"]["scope"] == "complete"
    assert session["stages"]["system"] == "in_progress"


def test_completing_the_system_stage_releases_held_findings_and_a_skip_does_not(system):
    system.go_to_stage("system")
    system.add_finding("differs", "shop", "README.md", "a queue", ["README.md"])
    assert [f["id"] for f in system.complete_stage()["released"]] == ["R1"]
    assert system["descriptionComplete"] is True

    other = Record.start("stride-threat-model", "Shop", "Ana Souza", "2026-11-21")
    other.go_to_stage("system")
    other.add_finding("differs", "shop", "README.md", "a queue", ["README.md"])
    assert other.request_change("skip_stage") == "applied"
    assert other["descriptionComplete"] is False
    assert other["findings"][0]["reported"] is False


def test_leaving_the_threats_stage_lists_what_was_not_looked_at(system):
    system.go_to_stage("threats")
    system.add_threat("C1", "spoofing", "x")
    uncovered = system.complete_stage()["uncovered"]
    assert ("C1", "spoofing") not in uncovered
    assert ("C1", "tampering") in uncovered
    assert ("F1", "spoofing") not in uncovered


def test_going_to_a_stage_leaves_the_one_left_as_it_was(session):
    session.go_to_stage("threats")
    assert session["stages"]["scope"] == "in_progress"
    assert session["stages"]["system"] == "not_started"
    assert session["stages"]["threats"] == "in_progress"


def test_the_last_stage_has_no_next(session):
    session.go_to_stage("model")
    assert session.complete_stage()["entered"] is None
    assert session["stages"]["model"] == "complete"
    assert session.in_progress


# --- skipping, finishing, abandoning ------------------------------------------


def test_one_participant_skips_at_once(session):
    assert session.request_change("skip_stage") == "applied"
    assert session["stages"]["scope"] == "skipped"
    assert session["stage"] == "system"
    assert session["pending"] is None


def test_several_participants_skip_only_on_a_later_message(session):
    session.add_person("Ben Okafor")
    assert session.request_change("skip_stage") == "pending"
    with pytest.raises(Refused):
        session.resolve_change(True)
    session.next_turn()
    assert session.resolve_change(True) == "skip_stage"
    assert session["stages"]["scope"] == "skipped"


@pytest.mark.parametrize("action, status", [("finish", "finished"), ("abandon", "abandoned")])
def test_finishing_and_abandoning_are_always_announced_first(session, action, status):
    assert session.request_change(action) == "pending"
    with pytest.raises(Refused):
        session.resolve_change(True)
    session.next_turn()
    assert session.resolve_change(True) == action
    assert session["status"] == status
    assert session["notesPostedOnTurn"] == session["turn"]


def test_a_finish_completes_the_model_stage_and_no_other(session):
    session.request_change("finish")
    session.next_turn()
    session.resolve_change(True)
    assert session["stages"]["model"] == "complete"
    assert session["stages"]["scope"] == "in_progress"
    assert ("scope", "in_progress") in session.unfinished_stages()


def test_an_objection_drops_the_request_and_a_new_one_is_needed(session):
    session.request_change("finish")
    session.next_turn()
    assert session.resolve_change(False) is None
    session.next_turn()
    with pytest.raises(Refused):
        session.resolve_change(True)
    assert session.in_progress


def test_a_second_request_replaces_the_first(session):
    session.add_person("Ben Okafor")
    session.request_change("skip_stage")
    session.next_turn()
    session.request_change("finish")
    with pytest.raises(Refused):
        session.resolve_change(True)
    assert session["pending"]["action"] == "finish"


# --- after the notes ----------------------------------------------------------


@pytest.fixture
def finished(system):
    system.add_threat("C1", "tampering", "x")
    system.add_mitigation("sign jobs", ["T1"])
    system.request_change("finish")
    system.next_turn()
    system.resolve_change(True)
    return system


def test_changes_after_the_notes_are_marked(finished):
    assert finished["threats"][0]["changedAfterNotes"] is False
    finished.add_threat("C2", "spoofing", "y")
    finished.rate_threat("T1", "high", "a", "high", "b")
    finished.add_mitigation("check signatures", ["T2"])
    assert [t["changedAfterNotes"] for t in finished["threats"]] == [True, True]
    assert finished["mitigations"][1]["changedAfterNotes"] is True


def test_removals_after_the_notes_are_listed(finished):
    finished.remove("T1")
    assert finished["removedAfterNotes"] == ["T1", "M1"]


def test_a_person_who_first_writes_after_the_end_joined_after_and_may_decide(finished):
    finished.add_person("Carla Mendes")
    finished.add_person("Ana Souza")
    assert finished["participants"] == ["Ana Souza"]
    assert finished["joinedAfter"] == ["Carla Mendes"]
    finished.decide_threat("T1", "mitigate", "", ["Carla Mendes"], "Carla Mendes")
    assert finished["threats"][0]["changedAfterNotes"] is True


def test_a_change_cannot_be_requested_once_the_session_has_ended(finished):
    with pytest.raises(Refused):
        finished.request_change("abandon")


# --- a request that is repeated, and one that never finished --------------------


def _handle(state, message_id, change, finish=True):
    """Handle one message the way main.py does, applying change to the record."""
    repeat = rec.begin_message(state, message_id)
    session = rec.load(state)
    if session:
        session.next_turn()
    session = change(session)
    rec.save(state, session)
    if finish:
        rec.end_message(state)
    return repeat


def _start(_):
    return Record.start("stride-threat-model", "Shop", "Ana Souza", "2026-11-21")


def _add_threat(session):
    if not session["elements"]:
        session.add_element("component", "API")
    session.add_threat("C1", "tampering", "x")
    return session


def test_a_repeated_message_is_recorded_once():
    state = FakeState()
    _handle(state, "C1:1", _start)
    assert _handle(state, "C1:2", _add_threat) is False
    assert _handle(state, "C1:2", _add_threat) is True
    session = rec.load(state)
    assert [t["id"] for t in session["threats"]] == ["T1"]
    assert session["turn"] == 2


def test_a_session_started_by_a_first_attempt_is_started_once():
    state = FakeState()
    _handle(state, "C1:1", _start, finish=False)
    assert rec.begin_message(state, "C1:1") is True
    assert rec.load(state) is None


def test_a_finish_cannot_be_confirmed_by_a_repeat_of_the_message_that_asked():
    state = FakeState()
    _handle(state, "C1:1", _start)

    def ask(session):
        session.request_change("finish")
        return session

    def confirm(session):
        with pytest.raises(Refused):
            session.resolve_change(True)
        return session

    def confirm_later(session):
        assert session.resolve_change(True) == "finish"
        return session

    _handle(state, "C1:2", ask)
    rec.begin_message(state, "C1:2")
    again = rec.load(state)
    again.next_turn()
    assert again["pending"] is None
    confirm(again)


def test_a_message_without_an_id_is_always_new():
    state = FakeState()
    _handle(state, None, _start)
    assert _handle(state, None, _add_threat) is False
    assert _handle(state, None, _add_threat) is False
    assert len(rec.load(state)["threats"]) == 2


def test_nothing_stays_recorded_from_a_message_whose_every_attempt_failed():
    state = FakeState()
    _handle(state, "C1:1", _start)
    _handle(state, "C1:2", _add_threat, finish=False)
    _handle(state, "C1:2", _add_threat, finish=False)
    assert len(rec.load(state)["threats"]) == 1  # the half-made change is still there

    def look(session):
        assert session["threats"] == []
        return session

    assert _handle(state, "C1:3", look) is False


def test_repositories_are_restored_with_the_record():
    state = FakeState()
    rec.begin_message(state, "C1:1")
    rec.save_repositories(state, [{"name": "shop", "listed": False}])
    assert rec.begin_message(state, "C1:1") is True
    assert rec.load_repositories(state) == []


def test_a_repeat_of_the_confirming_message_can_still_confirm():
    state = FakeState()
    _handle(state, "C1:1", _start)

    def ask(session):
        session.request_change("finish")
        return session

    def confirm(session):
        assert session.resolve_change(True) == "finish"
        return session

    _handle(state, "C1:2", ask)
    _handle(state, "C1:3", confirm, finish=False)
    assert _handle(state, "C1:3", confirm) is True
    assert rec.load(state)["status"] == "finished"
