"""The session record as text for the model.

The model sees only the most recent messages of a conversation, so it is given
the record afresh before every call. This is that text: compact, complete enough
to lead from, and silent about what must not be given away.

Nothing in this module logs.
"""

from session.record import STAGES
from session.render import STAGE_TITLES

NO_SESSION = "No threat modelling session is in progress in this conversation."

NOTES_RULE = (
    "These are your own notes for this stage. You MUST NOT reveal or describe them to the "
    "participants before the session ends."
)
END_WARNING = (
    "This thread stops being answered in less than a day. With this reply, tell the "
    "participants so, once, and offer to post the written model as it stands."
)


def _lines(title, items):
    return [title] + [f"  {item}" for item in items] if items else []


def _threat_line(threat):
    parts = [f"{threat['id']} {threat['category']} on {threat['element']}: {threat['description']}"]
    if threat["severity"]:
        parts.append(
            f"likelihood {threat['likelihood']}, impact {threat['impact']}, severity {threat['severity']}"
        )
    else:
        parts.append("not rated")
    if threat["decision"]:
        owner = threat["owner"] or ("none named" if threat["ownerAsked"] else "not asked yet")
        parts.append(
            f"decision {threat['decision']} by {', '.join(threat['decidedBy'])}, owner {owner}"
        )
    else:
        parts.append("no decision")
    return "; ".join(parts)


def _still_lacking(record):
    """What the current stage still lacks, so the model knows what to ask next."""
    stage = record["stage"]
    if stage == "threats":
        by_element = {}
        for element, category in record.uncovered():
            by_element.setdefault(element, []).append(category)
        return [f"{element}: {', '.join(categories)}" for element, categories in by_element.items()]
    if stage == "rating":
        return [t["id"] for t in record["threats"] if not t["severity"]]
    if stage == "mitigations":
        return [t["id"] for t in record["threats"] if not t["decision"]]
    return []


def _hints_and_notes(record):
    stage = record["stage"]
    here, elsewhere = [], []
    for hint in record["hints"]:
        about = hint["element"] or "the scope"
        if hint["stage"] == stage:
            state = "taken up" if hint["takenUp"] else "not taken up"
            here.append(f"{hint['id']} hint about {about} ({state}): {hint['point']}")
        else:
            elsewhere.append(f"{STAGE_TITLES[hint['stage']]}: {about}")
    for note in record["notes"]:
        if note["stage"] == stage:
            about = note["threat"] or note["mitigation"] or note["element"] or "the stage"
            here.append(f"{note['id']} note ({note['kind']}) about {about}: {note['text']}")
    lines = []
    if here:
        lines += [NOTES_RULE] + [f"  {item}" for item in here]
    if elsewhere:
        lines.append("Hints already given in other stages: " + "; ".join(elsewhere) + ".")
    other_notes = sum(1 for note in record["notes"] if note["stage"] != stage)
    if other_notes:
        lines.append(f"Notes kept in other stages: {other_notes}.")
    return lines


def summarise(record, repositories=None, thread_ends_at=None, warn_end=False):
    """Return the text the model is given about the session."""
    if record is None:
        lines = [NO_SESSION]
    else:
        lines = [
            f"Session: threat model of \"{record['system']}\", {record['status'].replace('_', ' ')}.",
            "Stages: " + ", ".join(f"{s} ({record['stages'][s].replace('_', ' ')})" for s in STAGES)
            + f". Current stage: {record['stage']}.",
            "Participants: " + ", ".join(record["participants"]) + ".",
        ]
        if record["joinedAfter"]:
            lines.append("Joined after the session: " + ", ".join(record["joinedAfter"]) + ".")
        if record.notes_posted:
            lines.append(
                "The facilitator's notes have been posted. Every change from now on is marked."
            )
        if record["pending"]:
            pending = record["pending"]
            lines.append(
                f"Pending: {pending['action']}, announced. Confirm it with resolve_change if this "
                "message does not object; drop it if it does."
            )
        lines += _lines("Scope:", [f"{i['id']} {i['kind']}: {i['text']}" for i in record["scope"]])
        elements = []
        for element in record["elements"]:
            if element["kind"] == "data_flow":
                elements.append(f"{element['id']} data flow {element['from']} → {element['to']}: {element['data']}")
            else:
                detail = f": {element['description']}" if element["description"] else ""
                elements.append(f"{element['id']} {element['kind'].replace('_', ' ')} \"{element['name']}\"{detail}")
        lines += _lines("Elements:", elements)
        lines += _lines("Trust boundaries:", [
            f"{b['id']} \"{b['name']}\" holds {', '.join(b['inside']) or 'nothing yet'}"
            for b in record["boundaries"]
        ])
        if record["stage"] == "system":
            lines.append("The participants have said their description is complete."
                         if record["descriptionComplete"]
                         else "The participants have not yet said their description is complete.")
        lines += _lines("Threats:", [_threat_line(t) for t in record["threats"]])
        lines += _lines("None found, by the participants' choice:", [
            f"{element}: {category}" for element, category in record["noneFound"]
        ])
        lines += _lines("Mitigations:", [
            f"{m['id']} for {', '.join(m['threats'])}: {m['description']}; owner {m['owner'] or 'none named'}"
            for m in record["mitigations"]
        ])
        lines += _lines("Open questions:", [f"{q['id']}: {q['text']}" for q in record["openQuestions"]])
        lines += _lines("Still to cover in this stage:", _still_lacking(record))
        held = sum(1 for finding in record["findings"] if not finding["reported"])
        if held:
            lines.append(
                f"Repository findings held back until the description is complete: {held}. "
                "Do not mention them yet."
            )
        lines += _hints_and_notes(record)

    listed = [r for r in repositories or [] if r.get("listed")]
    if listed:
        lines.append("Repositories listed: " + ", ".join(
            f"{r['name']} ({len(r.get('filesRead') or [])} files read)" for r in listed
        ) + ".")
    if thread_ends_at:
        lines.append(f"This thread stops being answered at {thread_ends_at} (UTC).")
    if warn_end:
        lines.append(END_WARNING)
    return "\n".join(lines)

