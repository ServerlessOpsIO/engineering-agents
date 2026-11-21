"""Unit tests for the record as text for the model."""

import pytest

from session import summary
from session.record import Record


@pytest.fixture
def session():
    s = Record.start("stride-threat-model", "Login service", "Ana Souza", "2026-11-21")
    s.add_scope_item("included", "The login API")
    s.complete_stage()
    s.add_element("component", "API", "Handles sign-in")
    s.add_element("data_store", "Users table")
    s.add_data_flow("C1", "DS1", "user rows")
    s.add_boundary("Internal", ["C1", "DS1"])
    return s


def test_no_record_says_there_is_no_session():
    assert summary.summarise(None) == summary.NO_SESSION


def test_it_gives_the_stage_the_people_and_what_was_recorded(session):
    text = summary.summarise(session)
    assert 'threat model of "Login service", in progress' in text
    assert "scope (complete), system (in progress), threats (not started)" in text
    assert "Current stage: system." in text
    assert "Participants: Ana Souza." in text
    assert "S1 included: The login API" in text
    assert 'C1 component "API": Handles sign-in' in text
    assert "F1 data flow C1 → DS1: user rows" in text
    assert 'TB1 "Internal" holds C1, DS1' in text
    assert "have not yet said their description is complete" in text


def test_the_threats_stage_lists_what_each_element_still_lacks(session):
    session.complete_stage()
    session.add_threat("C1", "spoofing", "forged token")
    session.none_found("C1", "tampering")
    text = summary.summarise(session)
    assert "T1 spoofing on C1: forged token; not rated; no decision" in text
    assert "C1: tampering" in text
    assert "Still to cover in this stage:" in text
    lacking = text.split("Still to cover in this stage:")[1]
    assert "C1: repudiation, information_disclosure" in lacking
    assert "F1: tampering, information_disclosure, denial_of_service" in lacking


def test_rating_and_mitigation_stages_list_the_threats_left(session):
    session.go_to_stage("rating")
    session.add_threat("C1", "spoofing", "x")
    session.add_threat("C1", "tampering", "y")
    session.rate_threat("T1", "high", "a", "low", "b")
    assert summary.summarise(session).split("Still to cover in this stage:")[1].strip().startswith("T2")
    session.go_to_stage("mitigations")
    session.decide_threat("T2", "mitigate", "", ["Ana Souza"])
    text = summary.summarise(session)
    assert "severity medium" in text
    assert "decision mitigate by Ana Souza, owner none named" in text
    assert text.split("Still to cover in this stage:")[1].strip().startswith("T1")


def test_hints_and_notes_of_the_current_stage_are_shown_under_the_rule(session):
    session.go_to_stage("threats")
    session.give_hint("C1", "who can call the API directly")
    session.add_note("not_raised", "no limit on sign-in attempts", element="C1")
    text = summary.summarise(session)
    assert summary.NOTES_RULE in text
    assert "H1 hint about C1 (not taken up): who can call the API directly" in text
    assert "N1 note (not_raised) about C1: no limit on sign-in attempts" in text


def test_hints_and_notes_of_other_stages_are_counted_and_not_shown(session):
    session.go_to_stage("threats")
    session.give_hint("C1", "zebra crossing")
    session.add_note("not_raised", "giraffe enclosure", element="C1")
    session.go_to_stage("rating")
    text = summary.summarise(session)
    assert "zebra" not in text and "giraffe" not in text
    assert summary.NOTES_RULE not in text
    assert "Hints already given in other stages: Threats: C1." in text
    assert "Notes kept in other stages: 1." in text


def test_a_held_finding_is_counted_and_its_text_is_not_shown(session):
    session.add_finding("not_mentioned", "shop", "README.md", "there is a flamingo queue", ["README.md"])
    text = summary.summarise(session)
    assert "held back until the description is complete: 1" in text
    assert "flamingo" not in text
    session.mark_description_complete()
    assert "held back" not in summary.summarise(session)


def test_a_pending_change_and_posted_notes_are_said(session):
    session.request_change("finish")
    assert "Pending: finish, announced." in summary.summarise(session)
    session.next_turn()
    session.resolve_change(True)
    session.add_person("Carla Mendes")
    text = summary.summarise(session)
    assert "finished" in text
    assert "The facilitator's notes have been posted." in text
    assert "Joined after the session: Carla Mendes." in text


def test_repositories_and_the_end_of_the_thread(session):
    repositories = [
        {"name": "shop", "listed": True, "filesRead": ["README.md"]},
        {"name": "other", "listed": False},
    ]
    text = summary.summarise(session, repositories, "2026-11-28T14:00:01Z", warn_end=True)
    assert "Repositories listed: shop (1 files read)." in text
    assert "other" not in text
    assert "stops being answered at 2026-11-28T14:00:01Z" in text
    assert summary.END_WARNING in text
    assert summary.END_WARNING not in summary.summarise(session, repositories, "2026-11-28T14:00:01Z")
