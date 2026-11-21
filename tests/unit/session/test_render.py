"""Unit tests for the written model and the facilitator's notes (contracts/written-model.md)."""

import re

import pytest

from session import render
from session.record import Record

HEADINGS = [
    "## Summary", "## Scope", "## System description", "## Data flow diagram",
    "## Threats", "## Coverage", "## Mitigations", "## Open questions", "## Method",
]
TODAY = "2026-11-22"


def model(record, repositories=None):
    return render.written_model(record, repositories or [], TODAY)


@pytest.fixture
def empty():
    return Record.start("stride-threat-model", "Login service", "Ana Souza", "2026-11-21")


@pytest.fixture
def full(empty):
    """A session taken through every stage, with one of most things."""
    s = empty
    s.add_person("Ben Okafor")
    s.add_scope_item("included", "The login API")
    s.add_scope_item("excluded", "The admin console")
    s.add_scope_item("assumption", "TLS ends at the gateway")
    s.complete_stage()
    s.add_element("component", "API", "Handles sign-in")
    s.add_element("component", "Worker")
    s.add_element("data_store", "Users table")
    s.add_element("external_party", "Browser")
    s.add_data_flow("EP1", "C1", "credentials")
    s.add_data_flow("C1", "DS1", "user rows")
    s.add_boundary("Internal network", ["C1", "C2", "DS1"])
    s.complete_stage()
    s.add_threat("C1", "spoofing", "A forged session token is accepted")
    s.add_threat("F1", "information_disclosure", "Credentials read in transit")
    s.add_threat("DS1", "tampering", "Rows changed by the worker")
    s.none_found("C1", "tampering")
    s.complete_stage()
    s.rate_threat("T1", "medium", "needs a stolen key", "high", "full account takeover")
    s.rate_threat("T2", "low", "TLS everywhere", "high", "passwords exposed")
    s.complete_stage()
    s.add_mitigation("Rotate signing keys monthly", ["T1"], "Platform team")
    s.decide_threat("T1", "mitigate", "", ["Ana Souza", "Ben Okafor"], "Ben Okafor")
    s.decide_threat("T2", "accept", "TLS is enforced", ["Ana Souza"])
    s.decide_threat("T3", "mitigate", "", ["Ben Okafor"])
    s.add_open_question("Who reviews the accepted risk each year?")
    s.complete_stage()
    return s


def finish(record):
    record.request_change("finish")
    record.next_turn()
    record.resolve_change(True)
    return record


def section(text, heading):
    after = text.split(heading + "\n", 1)[1]
    return re.split(r"\n## ", after, maxsplit=1)[0]


# --- structure ----------------------------------------------------------------


def test_every_section_is_present_and_in_order_even_for_an_empty_record(empty):
    text = model(empty)
    assert text.startswith("# Threat model: Login service\n")
    assert re.findall(r"^## .*$", text, re.M) == HEADINGS


def test_an_empty_record_says_so_in_each_section(empty):
    text = model(empty)
    assert section(text, "## Scope").count("None recorded.") == 3
    assert "No elements recorded." in section(text, "## Data flow diagram")
    assert "No threats recorded." in section(text, "## Threats")
    assert "None." in section(text, "## Open questions")


def test_the_same_record_gives_the_same_document(full):
    assert model(full) == model(full)


# --- status -------------------------------------------------------------------


def test_status_in_progress_lists_unfinished_stages(empty):
    text = model(empty)
    assert "> Status: **In progress**." in text
    assert "> Not finished: Scope." in text
    assert "> Not finished: Rating." in text
    assert "The written model" not in text.split("## Summary")[0]


def test_status_complete_when_finished_with_every_stage_done(full):
    head = model(finish(full)).split("## Summary")[0]
    assert "> Status: **Complete**." in head
    assert "Not finished" not in head and "Skipped" not in head


def test_status_finished_when_a_stage_was_skipped(empty):
    empty.request_change("skip_stage")
    head = model(finish(empty)).split("## Summary")[0]
    assert "> Status: **Finished**." in head
    assert "> Skipped: Scope." in head
    assert "> Not finished: System." in head


def test_status_abandoned(empty):
    empty.request_change("abandon")
    empty.next_turn()
    empty.resolve_change(True)
    assert "> Status: **Abandoned**." in model(empty)


def test_a_skipped_stages_section_begins_with_the_same_words(empty):
    empty.request_change("skip_stage")
    text = model(empty)
    assert section(text, "## Scope").startswith("\nSkipped: Scope.")
    assert section(text, "## Threats").startswith("\nNot finished: Threats.")


# --- summary ------------------------------------------------------------------


def test_the_summary_counts_threats_by_severity_and_names_people(full):
    summary = section(model(full), "## Summary")
    assert "- **System**: Login service" in summary
    assert f"- **Date**: {TODAY}" in summary
    assert "- **Session started**: 2026-11-21" in summary
    assert "- **Participants**: Ana Souza, Ben Okafor" in summary
    assert "Critical 0, High 1, Medium 1, Low 0, Note 0, Not rated 1" in summary
    assert "Joined after" not in summary


def test_people_who_joined_after_the_session_are_listed_apart(full):
    finish(full).add_person("Carla Mendes")
    summary = section(model(full), "## Summary")
    assert "- **Participants**: Ana Souza, Ben Okafor" in summary
    assert "- **Joined after the session**: Carla Mendes" in summary


# --- system and diagram -------------------------------------------------------


def test_the_system_description_lists_elements_boundaries_and_files(full):
    repositories = [{
        "name": "login-service", "listed": True, "commit": "0123456789abcdef",
        "filesRead": ["README.md", "template.yaml"], "unread": "rate_limited",
    }]
    text = section(model(full, repositories), "## System description")
    assert "| C1 | Component | API | Handles sign-in |" in text
    assert "| F1 | Data flow | EP1 → C1 | credentials |" in text
    assert "| TB1 | Internal network | C1, C2, DS1 |" in text
    assert "- `login-service@0123456`: `README.md`" in text
    assert "`login-service` could not be read in full." in text
    assert "None." in section(model(full), "## System description")


def test_the_diagram_draws_each_kind_boundaries_and_flows(full):
    text = section(model(full), "## Data flow diagram")
    assert text.strip().startswith("```mermaid\nflowchart LR")
    assert '    subgraph TB1["TB1: Internal network"]' in text
    assert '        C1["C1: API"]' in text
    assert '        DS1[("DS1: Users table")]' in text
    assert '    EP1("EP1: Browser")' in text
    assert '    EP1 -->|"F1: credentials"| C1' in text
    assert text.strip().endswith("```")


def test_an_element_in_two_boundaries_is_drawn_once(full):
    full.add_boundary("PCI zone", ["C1"])
    text = render.diagram(full)
    assert text.count('C1["C1: API"]') == 1
    assert "%% C1 is also inside TB2" in text


def test_names_cannot_break_the_diagram(empty):
    empty.add_element("component", 'API "v2" [beta] | `x` (new) <b>; #1\nline two')
    empty.add_element("external_party", "User")
    empty.add_data_flow("EP1", "C1", 'a "quoted" | [thing]')
    text = render.diagram(empty)
    label = re.search(r'C1\["(.*)"\]', text).group(1)
    assert not re.search(r'["\[\]|`()<>;#\n]', label)
    assert "API 'v2' beta" in label
    edge = re.search(r'-->\|"(.*)"\|', text).group(1)
    assert not re.search(r'["\[\]|]', edge)


# --- threats ------------------------------------------------------------------


def test_the_threat_table_has_every_column_and_is_ordered_by_severity(full):
    text = section(model(full), "## Threats")
    assert ("| ID | Category | Element | Threat | Likelihood | Impact | Severity | Decision "
            "| Decided by | Owner |") in text
    rows = [line for line in text.splitlines() if line.startswith("| T")]
    assert [row.split(" | ")[0] for row in rows] == ["| T1", "| T2", "| T3"]
    assert ("| T1 | Spoofing | C1 (API) | A forged session token is accepted "
            "| Medium: needs a stolen key | High: full account takeover | High | Mitigate "
            "| Ana Souza, Ben Okafor | Ben Okafor |") in text
    assert "| Accept: TLS is enforced | Ana Souza | None named |" in text
    assert rows[2].count("—") == 3  # T3 has no rating
    assert "| F1 (EP1 → C1) |" in text


def test_threats_with_the_same_severity_are_ordered_by_number(empty):
    empty.add_element("component", "API")
    for _ in range(11):
        empty.add_threat("C1", "tampering", "x")
    for number in (10, 2):
        empty.rate_threat(f"T{number}", "high", "a", "high", "b")
    rows = [l.split(" | ")[0] for l in section(model(empty), "## Threats").splitlines()
            if l.startswith("| T")]
    assert rows[:3] == ["| T2", "| T10", "| T1"]


def test_text_from_people_cannot_break_a_table(empty):
    empty.add_element("component", "API")
    empty.add_threat("C1", "tampering", "# heading | pipe\nsecond line")
    row = [l for l in model(empty).splitlines() if l.startswith("| T1")][0]
    assert "\\# heading \\| pipe second line" in row
    assert row.count(" | ") == 9


# --- coverage -----------------------------------------------------------------


def test_coverage_has_a_row_for_each_element_and_four_kinds_of_cell(full):
    text = section(model(full), "## Coverage")
    assert "| Element | S | T | R | I | D | E |" in text
    assert "| C1 (API) | T1 | None found | Not considered | Not considered | Not considered | Not considered |" in text
    assert "| F1 (EP1 → C1) | n/a | Not considered | n/a | T2 | Not considered | n/a |" in text
    assert "| EP1 (Browser) | Not considered | n/a | Not considered | n/a | n/a | n/a |" in text
    assert "S: spoofing, T: tampering" in text


# --- mitigations and open questions -------------------------------------------


def test_mitigations_and_threats_left_without_one(full):
    text = section(model(full), "## Mitigations")
    assert "| M1 | Rotate signing keys monthly | T1 | Platform team |" in text
    assert "**Threats to be mitigated with no mitigation recorded**\n\n- T3" in text


def test_open_questions_are_numbered(full):
    assert "1. Who reviews the accepted risk each year?" in section(model(full), "## Open questions")


def test_the_method_names_both_methods_with_links(empty):
    method = section(model(empty), "## Method")
    assert "[STRIDE](" in method and "[OWASP Risk Rating Methodology](" in method
    assert "an AI agent" in method


# --- after the notes ----------------------------------------------------------


def test_changes_and_removals_after_the_notes_are_marked(full):
    finish(full)
    assert "†" not in model(full)
    full.add_threat("C2", "denial_of_service", "Queue flooded")
    full.add_mitigation("Rate limit", ["T4"])
    full.remove("T3")
    text = model(full)
    head = text.split("## Summary")[0]
    assert "> Entries marked † were added or changed after the facilitator's notes were posted." in head
    assert "> Removed after the facilitator's notes were posted: T3." in head
    assert "| T4† |" in text and "| M2† |" in text
    assert "| T1 |" in text


# --- the facilitator's notes --------------------------------------------------


def test_the_notes_have_three_sections_and_say_whose_they_are(empty):
    text = render.facilitator_notes(empty)
    assert text.startswith("# Facilitator's notes: Login service\n")
    assert "STRIDEr's own observations" in text and "have not\n> checked them" in text
    assert re.findall(r"^## .*$", text, re.M) == [
        "## Hinted at, and not taken up", "## Not raised in the session", "## Questioned, and kept",
    ]
    assert text.count("Nothing.") == 3


def test_the_notes_hold_untaken_hints_unraised_points_and_kept_ratings(full):
    full.go_to_stage("threats")
    taken = full.give_hint("C1", "who can call the API directly")
    full.give_hint("C2", "what the worker trusts from the queue")
    full.hint_taken_up(taken["id"])
    full.add_note("not_raised", "no limit on sign-in attempts", element="C1")
    full.add_note("questioned_kept", "low likelihood although keys are shared", threat="T2")
    text = render.facilitator_notes(full)
    assert "who can call the API directly" not in text
    assert "- Threats, C2 (Worker): what the worker trusts from the queue" in text
    assert "- Threats, C1 (API): no limit on sign-in attempts (not raised in the session)" in text
    assert "- T2: low likelihood although keys are shared" in text


def test_nothing_from_the_notes_is_in_the_model(full):
    full.go_to_stage("threats")
    full.give_hint("C2", "zebra crossing")
    full.add_note("not_raised", "giraffe enclosure", element="C1")
    text = model(full)
    assert "zebra" not in text and "giraffe" not in text


# --- file names and titles ----------------------------------------------------


@pytest.mark.parametrize("system, kind, expected", [
    ("Login service", render.MODEL, "threat-model-login-service.md"),
    ("Login service", render.NOTES, "facilitator-notes-login-service.md"),
    ("  Pay/ments  API (v2)! ", render.MODEL, "threat-model-pay-ments-api-v2.md"),
    ("???", render.MODEL, "threat-model.md"),
    ("", render.NOTES, "facilitator-notes.md"),
])
def test_file_names(system, kind, expected):
    assert render.filename(system, kind) == expected


def test_a_long_name_is_cut(empty):
    name = render.filename("x" * 200, render.MODEL)
    assert len(name) == 60 + len(".md") and name.endswith(".md")


def test_titles_keep_the_name_as_given():
    assert render.title("Login service", render.MODEL) == "Threat model: Login service"
    assert render.title("Login service", render.NOTES) == "Facilitator's notes: Login service"
