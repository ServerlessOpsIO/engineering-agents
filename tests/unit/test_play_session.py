"""Unit tests for the command that plays the fixed session. Nothing here calls AWS."""

import pytest

import play_session as play
from session import render
from session.record import Record


def record():
    s = Record.start("stride-threat-model", "URL shortener", "Ana Souza", "2026-11-21")
    s.add_person("Ben Okafor")
    s.add_scope_item("included", "The API")
    s.complete_stage()
    s.add_element("component", "API")
    s.add_element("data_store", "Links table")
    s.add_element("external_party", "Browser")
    s.add_data_flow("EP1", "C1", "a long URL")
    s.add_boundary("AWS account", ["C1", "DS1"])
    s.complete_stage()
    s.add_threat("C1", "spoofing", "Links created as another customer")
    s.none_found("F1", "information_disclosure")
    s.give_hint("DS1", "who else can write to the giraffe enclosure table")
    s.complete_stage()
    s.rate_threat("T1", "medium", "keys leak into logs", "high", "any customer")
    s.add_note("questioned_kept", "low likelihood although the endpoint is public", threat="T1")
    s.complete_stage()
    s.add_mitigation("Move the key to a header", ["T1"], "Ben Okafor")
    s.decide_threat("T1", "mitigate", "", ["Ana Souza"], "Ben Okafor")
    s.complete_stage()
    return s


def documents(s, notes):
    out = [{"filename": render.filename(s["system"], render.MODEL),
            "markdown": render.written_model(s, [], "2026-11-22")}]
    if notes:
        out.append({"filename": render.filename(s["system"], render.NOTES),
                    "markdown": render.facilitator_notes(s)})
    return out


@pytest.fixture
def played():
    """The replies a good agent would give to a short session with every kind of turn."""
    s = record()
    part_way = documents(s, notes=False)
    s.request_change("finish")
    s.next_turn()
    s.resolve_change(True)
    finished = documents(s, notes=True)
    s.add_threat("DS1", "tampering", "Rows overwritten")
    changed = documents(s, notes=True)
    spec = {
        "turns": [
            {"speaker": "Ana Souza", "text": "start", "addressed": True, "expect": "answer", "opening": True},
            {"speaker": "Ben Okafor", "text": "Ana, lunch?", "expect": "no_reply"},
            {"speaker": "Ben Okafor", "text": "the model?", "documents": 1, "part_way_model": True},
            {"speaker": "Ana Souza", "text": "finish", "documents": 0},
            {"speaker": "Ben Okafor", "text": "agreed", "documents": 2, "finishes": True},
            {"speaker": "Ana Souza", "text": "one more", "documents": 2, "changed_after_notes": True},
        ],
        "must_appear_in_notes": ["T1"],
        "must_not_appear_in_model": ["giraffe"],
    }
    replies = [
        {"kind": "answer", "text": "Scope, system, threats, rating, mitigations, then the model."},
        {"kind": "no_reply", "text": ""},
        {"kind": "answer", "text": "Attached.", "documents": part_way},
        {"kind": "answer", "text": "About to post."},
        {"kind": "answer", "text": "Posted.", "documents": finished},
        {"kind": "answer", "text": "Posted again.", "documents": changed},
    ]
    return spec, replies


def run(spec, replies):
    queue = list(replies)
    return play.play(spec, lambda payload: queue.pop(0))


def failed(found, kind=None):
    return [name for k, name, passed, _ in found if not passed and (kind is None or k == kind)]


# --- the session file ---------------------------------------------------------


def test_the_fixed_session_has_two_named_participants_and_every_kind_of_turn():
    spec = play.load_session(play.DEFAULT_SESSION)
    turns = spec["turns"]
    assert len({turn["speaker"] for turn in turns}) >= 2
    assert sum(1 for t in turns if t.get("expect") == "no_reply") >= 2
    assert sum(1 for t in turns if "ASKS FOR THE WORK" in str(t.get("note"))) >= 3
    assert any(t.get("part_way_model") for t in turns)
    assert any(t.get("finishes") for t in turns)
    assert any(t.get("changed_after_notes") for t in turns)
    assert any("OBJECTION" in str(t.get("note")) for t in turns)
    assert turns[0].get("opening") and turns[0].get("addressed")


def test_a_turn_becomes_a_request_with_its_own_message_id():
    payload = play.payload_for(3, {"speaker": "Ana Souza", "text": "two\n  lines"}, "2026-11-28T10:00:00Z")
    assert payload == {
        "prompt": "two lines", "speakerName": "Ana Souza", "conversationType": "channel_thread",
        "addressed": False, "messageId": "play:3", "threadEndsAt": "2026-11-28T10:00:00Z",
    }
    direct = play.payload_for(1, {"speaker": "Ana", "text": "x", "type": "direct_message"}, "t")
    assert "threadEndsAt" not in direct


# --- the written model's structure --------------------------------------------


def test_a_model_made_by_the_renderer_has_nothing_wrong():
    assert play.check_model(render.written_model(record(), [], "2026-11-22")) == []
    empty = Record.start("stride-threat-model", "Shop", "Ana Souza", "2026-11-21")
    assert play.check_model(render.written_model(empty, [], "2026-11-22")) == []


@pytest.mark.parametrize("heading", play.MODEL_HEADINGS)
def test_a_missing_section_is_reported_by_name(heading):
    text = render.written_model(record(), [], "2026-11-22").replace(heading + "\n", "")
    assert f"the section {heading[3:]}" in play.check_model(text)


def test_other_faults_are_reported():
    good = render.written_model(record(), [], "2026-11-22")
    assert "the status line" in play.check_model(good.replace("> Status:", "> State:"))
    assert "Participants in the summary" in play.check_model(good.replace("- **Participants**", "- **People**"))
    assert "the diagram" in play.check_model(good.replace("flowchart LR", "graph"))
    assert "an empty field in the threat row T1" in play.check_model(good.replace("| Spoofing |", "|  |"))
    assert "a result in the coverage row C1 (API)" in play.check_model(good.replace("| C1 (API) | T1 |", "| C1 (API) | maybe |"))
    without_row = "\n".join(l for l in good.splitlines() if not l.startswith("| DS1 (Links table) |"))
    assert "a coverage row for DS1" in play.check_model(without_row)


# --- the checks ---------------------------------------------------------------


def test_a_good_play_passes_every_check(played):
    spec, replies = played
    found = play.checks(spec, run(spec, replies))
    assert failed(found) == []
    names = [name for _, name, _, _ in found]
    assert "a change after the notes is marked †" in names
    assert "nothing from the notes is in the model" in names
    assert "the final written model has every part and field" in names


def test_notes_with_a_part_way_model_fail(played):
    spec, replies = played
    replies[2]["documents"] = replies[4]["documents"]
    found = play.checks(spec, run(spec, replies))
    assert "turn 3: 1 document(s)" in failed(found, play.STRUCTURAL)
    assert "turn 3: a part-way model comes without the notes" in failed(found, play.STRUCTURAL)


def test_a_finish_without_the_notes_fails(played):
    spec, replies = played
    replies[4]["documents"] = replies[4]["documents"][:1]
    assert "turn 5: the finish carries the model and the notes" in failed(
        play.checks(spec, run(spec, replies)), play.STRUCTURAL)


def test_a_point_from_the_notes_in_the_model_fails(played):
    spec, replies = played
    model = replies[5]["documents"][0]
    model["markdown"] += "\nwho else can write to the giraffe enclosure table\n"
    found = play.checks(spec, run(spec, replies))
    assert "nothing from the notes is in the model" in failed(found, play.STRUCTURAL)
    assert "the model does not contain 'giraffe'" in failed(found, play.BEHAVIOURAL)


def test_a_change_after_the_notes_without_its_mark_fails(played):
    spec, replies = played
    replies[5]["documents"] = replies[4]["documents"]
    assert "a change after the notes is marked †" in failed(
        play.checks(spec, run(spec, replies)), play.STRUCTURAL)


def test_a_wrong_kind_of_reply_is_a_behavioural_miss(played):
    spec, replies = played
    replies[1] = {"kind": "answer", "text": "Enjoy lunch."}
    found = play.checks(spec, run(spec, replies))
    assert failed(found, play.STRUCTURAL) == []
    assert failed(found, play.BEHAVIOURAL) == ["turn 2: expected no_reply"]


def test_a_turn_that_fails_or_is_slow_is_structural(played, monkeypatch):
    spec, replies = played
    queue = list(replies)

    def send(payload):
        if payload["messageId"] == "play:4":
            raise RuntimeError("the agent fell over")
        return queue.pop(0) if payload["messageId"] != "play:4" else None

    results = play.play(spec, lambda p: (queue.pop(0), send(p))[1] if p["messageId"] == "play:4" else queue.pop(0))
    results[0]["seconds"] = 140
    found = failed(play.checks(spec, results), play.STRUCTURAL)
    assert "turn 4: a reply came back" in found
    assert "turn 1: answered within 100 seconds" in found


def test_no_written_model_at_all_fails():
    spec = {"turns": [{"speaker": "Ana", "text": "hi"}]}
    found = play.checks(spec, run(spec, [{"kind": "answer", "text": "Hello."}]))
    assert failed(found, play.STRUCTURAL) == ["a written model was produced"]


# --- the transcript and the report --------------------------------------------


def test_the_transcript_and_the_documents_are_written_to_the_folder(played, tmp_path):
    spec, replies = played
    results = run(spec, replies)
    report = play.report_of(play.checks(spec, results))
    play.write_transcript(tmp_path / "run", results, report)
    names = sorted(p.name for p in (tmp_path / "run").iterdir())
    assert "transcript.md" in names and "checks.txt" in names
    assert "turn-03-threat-model-url-shortener.md" in names
    assert "turn-05-facilitator-notes-url-shortener.md" in names
    transcript = (tmp_path / "run" / "transcript.md").read_text()
    assert "**Ben Okafor**:" in transcript and "_(no reply)_" in transcript
    assert "Structural: all pass." in report


def test_the_report_says_how_many_failed(played):
    spec, replies = played
    replies[4]["documents"] = []
    report = play.report_of(play.checks(spec, run(spec, replies)))
    assert "FAIL  turn 5: 2 document(s) (got 0)" in report
    assert "FAILED" in report.splitlines()[-1]


def test_the_command_needs_a_runtime(monkeypatch, capsys):
    monkeypatch.delenv("AGENT_RUNTIME_ARN", raising=False)
    with pytest.raises(SystemExit):
        play.main([])
