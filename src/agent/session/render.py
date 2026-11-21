"""The written model and the facilitator's notes, made from the session record.

Both are GitHub-flavoured Markdown. The same record always gives the same
document: nothing here asks a model for words. The format is
specs/008-threat-model-session/contracts/written-model.md.

Nothing in this module logs. The documents hold what people said and their names.
"""

import re

from session.record import ABANDONED, CATEGORIES, FINISHED, SEVERITIES

EMPTY = "—"
CHANGED = "†"

STAGE_TITLES = {
    "scope": "Scope",
    "system": "System",
    "threats": "Threats",
    "rating": "Rating",
    "mitigations": "Mitigations and decisions",
    "model": "The written model",
}
CATEGORY_TITLES = {
    "spoofing": "Spoofing",
    "tampering": "Tampering",
    "repudiation": "Repudiation",
    "information_disclosure": "Information disclosure",
    "denial_of_service": "Denial of service",
    "elevation_of_privilege": "Elevation of privilege",
}
CATEGORY_LETTERS = {category: CATEGORY_TITLES[category][0] for category in CATEGORIES}
KIND_TITLES = {
    "component": "Component",
    "data_store": "Data store",
    "external_party": "External party",
    "data_flow": "Data flow",
}
COVERAGE_WORDS = {"none_found": "None found", "not_considered": "Not considered", "n/a": "n/a"}

STRIDE_LINK = "https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats"
OWASP_LINK = "https://owasp.org/www-community/OWASP_Risk_Rating_Methodology"

MODEL = "model"
NOTES = "notes"
_FILE_STEMS = {MODEL: "threat-model", NOTES: "facilitator-notes"}
_TITLES = {MODEL: "Threat model", NOTES: "Facilitator's notes"}
_FILENAME_CHARS = 60


def _text(value):
    """Return what a person gave, made safe for a table cell or a list item."""
    value = re.sub(r"\s+", " ", str(value or "")).strip().replace("|", "\\|")
    if value[:1] in ("#", ">"):
        value = "\\" + value
    return value


def _cell(value):
    return _text(value) or EMPTY


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _number(identifier):
    digits = re.sub(r"\D", "", identifier)
    return int(digits) if digits else 0


def filename(system, kind):
    """Return the file name for a document about the system."""
    stem = _FILE_STEMS[kind]
    slug = re.sub(r"[^a-z0-9]+", "-", str(system or "").lower()).strip("-")
    name = f"{stem}-{slug}" if slug else stem
    return name[:_FILENAME_CHARS].rstrip("-") + ".md"


def title(system, kind):
    return f"{_TITLES[kind]}: {_text(system)}"


# --- the written model --------------------------------------------------------


def _unfinished(record):
    """Stages that are not complete, leaving out the last, which is this document."""
    return [(stage, status) for stage, status in record.unfinished_stages() if stage != "model"]


def _status(record):
    unfinished = _unfinished(record)
    if record["status"] == FINISHED:
        word = "Finished" if unfinished else "Complete"
    elif record["status"] == ABANDONED:
        word = "Abandoned"
    else:
        word = "In progress"
    lines = [f"> Status: **{word}**."]
    for stage, status in unfinished:
        label = "Skipped" if status == "skipped" else "Not finished"
        lines.append(f"> {label}: {STAGE_TITLES[stage]}.")
    changed = any(item["changedAfterNotes"] for item in record["threats"] + record["mitigations"])
    if changed:
        lines.append(
            f"> Entries marked {CHANGED} were added or changed after the facilitator's notes were posted."
        )
    if record["removedAfterNotes"]:
        lines.append(
            "> Removed after the facilitator's notes were posted: "
            + ", ".join(record["removedAfterNotes"]) + "."
        )
    return "\n".join(lines)


def _stage_note(record, stage):
    """The words a section begins with when its stage was skipped or never started."""
    status = record["stages"][stage]
    if status == "skipped":
        return f"Skipped: {STAGE_TITLES[stage]}.\n\n"
    if status == "not_started":
        return f"Not finished: {STAGE_TITLES[stage]}.\n\n"
    return ""


def _summary(record, today):
    counts = {severity: 0 for severity in SEVERITIES}
    unrated = 0
    for threat in record["threats"]:
        if threat["severity"]:
            counts[threat["severity"]] += 1
        else:
            unrated += 1
    by_severity = ", ".join(f"{severity.capitalize()} {counts[severity]}" for severity in SEVERITIES)
    lines = [
        f"- **System**: {_text(record['system'])}",
        f"- **Date**: {today}",
        f"- **Session started**: {record['startedOn']}",
        "- **Participants**: " + (", ".join(_text(n) for n in record["participants"]) or EMPTY),
    ]
    if record["joinedAfter"]:
        lines.append(
            "- **Joined after the session**: " + ", ".join(_text(n) for n in record["joinedAfter"])
        )
    lines.append(f"- **Threats by severity**: {by_severity}, Not rated {unrated}")
    return "\n".join(lines)


def _scope(record):
    parts = []
    for kind, heading in (("included", "In scope"), ("excluded", "Out of scope"),
                          ("assumption", "Assumptions")):
        items = [item for item in record["scope"] if item["kind"] == kind]
        body = "\n".join(f"- {_text(item['text'])}" for item in items) or "None recorded."
        parts.append(f"**{heading}**\n\n{body}")
    return "\n\n".join(parts)


def _system(record, repositories):
    rows = []
    for element in record["elements"]:
        if element["kind"] == "data_flow":
            name, description = f"{element['from']} → {element['to']}", element["data"]
        else:
            name, description = element["name"], element["description"]
        rows.append([element["id"], KIND_TITLES[element["kind"]], _cell(name), _cell(description)])
    elements = (_table(["Identifier", "Kind", "Name", "Description"], rows)
                if rows else "No elements recorded.")
    boundaries = _table(
        ["Identifier", "Trust boundary", "Inside"],
        [[b["id"], _cell(b["name"]), ", ".join(b["inside"]) or EMPTY] for b in record["boundaries"]],
    ) if record["boundaries"] else "No trust boundaries recorded."

    files, unread = [], []
    for repository in repositories or []:
        commit = (repository.get("commit") or "")[:7]
        for path in repository.get("filesRead") or []:
            files.append(f"- `{repository['name']}@{commit}`: `{path}`")
        if repository.get("unread"):
            unread.append(f"`{repository['name']}` could not be read in full.")
    read = "\n".join(files) if files else "None."
    if unread:
        read += "\n\n" + " ".join(unread)
    return f"{elements}\n\n{boundaries}\n\n**Repository files read**\n\n{read}"


def _label(text):
    """Return text made safe for a Mermaid label in double quotes."""
    text = re.sub(r"\s+", " ", str(text or "")).replace('"', "'")
    return re.sub(r"[\[\]{}()<>|`#;]", "", text).strip()


def _node(element):
    label = _label(f"{element['id']}: {element['name']}")
    if element["kind"] == "data_store":
        return f'{element["id"]}[("{label}")]'
    if element["kind"] == "external_party":
        return f'{element["id"]}("{label}")'
    return f'{element["id"]}["{label}"]'


def diagram(record):
    """Return the data flow diagram as a fenced Mermaid block, or a sentence when empty."""
    nodes = [e for e in record["elements"] if e["kind"] != "data_flow"]
    flows = [e for e in record["elements"] if e["kind"] == "data_flow"]
    if not nodes:
        return "No elements recorded."
    by_id = {element["id"]: element for element in nodes}
    lines, drawn = ["flowchart LR"], set()
    for boundary in record["boundaries"]:
        lines.append(f'    subgraph {boundary["id"]}["{_label(boundary["id"] + ": " + boundary["name"])}"]')
        for identifier in boundary["inside"]:
            if identifier in drawn:
                lines.append(f"        %% {identifier} is also inside {boundary['id']}")
            elif identifier in by_id:
                lines.append("        " + _node(by_id[identifier]))
                drawn.add(identifier)
        lines.append("    end")
    lines.extend("    " + _node(element) for element in nodes if element["id"] not in drawn)
    for flow in flows:
        label = _label(f"{flow['id']}: {flow['data']}")
        lines.append(f'    {flow["from"]} -->|"{label}"| {flow["to"]}')
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def _element_name(record, identifier):
    for element in record["elements"]:
        if element["id"] == identifier:
            if element["kind"] == "data_flow":
                return f"{identifier} ({element['from']} → {element['to']})"
            return f"{identifier} ({_text(element['name'])})"
    return identifier


def _marked(item):
    return item["id"] + (CHANGED if item["changedAfterNotes"] else "")


def _rated(level, reason):
    return f"{level.capitalize()}: {_text(reason)}" if level else EMPTY


def _threats(record):
    if not record["threats"]:
        return "No threats recorded."

    def order(threat):
        rank = SEVERITIES.index(threat["severity"]) if threat["severity"] else len(SEVERITIES)
        return rank, _number(threat["id"])

    rows = []
    for threat in sorted(record["threats"], key=order):
        decision = EMPTY
        if threat["decision"]:
            decision = threat["decision"].capitalize()
            if threat["decisionReason"]:
                decision += f": {_text(threat['decisionReason'])}"
        owner = EMPTY
        if threat["decision"]:
            owner = _text(threat["owner"]) or "None named"
        rows.append([
            _marked(threat),
            CATEGORY_TITLES[threat["category"]],
            _element_name(record, threat["element"]),
            _cell(threat["description"]),
            _rated(threat["likelihood"], threat["likelihoodReason"]),
            _rated(threat["impact"], threat["impactReason"]),
            threat["severity"].capitalize() if threat["severity"] else EMPTY,
            decision,
            ", ".join(_text(name) for name in threat["decidedBy"]) or EMPTY,
            owner,
        ])
    return _table(
        ["ID", "Category", "Element", "Threat", "Likelihood", "Impact", "Severity",
         "Decision", "Decided by", "Owner"],
        rows,
    )


def _coverage(record):
    if not record["elements"]:
        return "No elements recorded."
    rows = []
    for element in record["elements"]:
        cells = record.coverage(element)
        rows.append([_element_name(record, element["id"])] + [
            ", ".join(cells[c]) if isinstance(cells[c], list) else COVERAGE_WORDS[cells[c]]
            for c in CATEGORIES
        ])
    legend = ", ".join(f"{CATEGORY_LETTERS[c]}: {CATEGORY_TITLES[c].lower()}" for c in CATEGORIES)
    return _table(["Element"] + [CATEGORY_LETTERS[c] for c in CATEGORIES], rows) + f"\n\n{legend}."


def _mitigations(record):
    body = _table(
        ["ID", "Mitigation", "Addresses", "Owner"],
        [[_marked(m), _cell(m["description"]), ", ".join(m["threats"]), _text(m["owner"]) or "None named"]
         for m in record["mitigations"]],
    ) if record["mitigations"] else "No mitigations recorded."
    addressed = {t for m in record["mitigations"] for t in m["threats"]}
    bare = [t["id"] for t in record["threats"]
            if t["decision"] == "mitigate" and t["id"] not in addressed]
    if bare:
        body += ("\n\n**Threats to be mitigated with no mitigation recorded**\n\n"
                 + "\n".join(f"- {identifier}" for identifier in bare))
    return body


def _open_questions(record):
    if not record["openQuestions"]:
        return "None."
    return "\n".join(f"{n}. {_text(q['text'])}" for n, q in enumerate(record["openQuestions"], 1))


METHOD = (
    "> This model was made in a session led by STRIDEr, an AI agent. The participants named\n"
    "> the threats, rated them and decided what to do. STRIDEr asked the questions and\n"
    f"> recorded the answers. Threats were looked for with [STRIDE]({STRIDE_LINK}), element by\n"
    "> element. Likelihood and impact were judged by the participants as high, medium or low,\n"
    f"> and severity was read from the table of the\n"
    f"> [OWASP Risk Rating Methodology]({OWASP_LINK})."
)


def written_model(record, repositories, today):
    """Return the written model for the record as it stands."""
    sections = [
        (f"# {title(record['system'], MODEL)}", _status(record)),
        ("## Summary", _summary(record, today)),
        ("## Scope", _stage_note(record, "scope") + _scope(record)),
        ("## System description", _stage_note(record, "system") + _system(record, repositories)),
        ("## Data flow diagram", diagram(record)),
        ("## Threats", _stage_note(record, "threats") + _threats(record)),
        ("## Coverage", _coverage(record)),
        ("## Mitigations", _stage_note(record, "mitigations") + _mitigations(record)),
        ("## Open questions", _open_questions(record)),
        ("## Method", METHOD),
    ]
    return "\n\n".join(f"{heading}\n\n{body}" for heading, body in sections) + "\n"


# --- the facilitator's notes --------------------------------------------------

NOTES_OPENING = (
    "> These are STRIDEr's own observations from the session. The participants have not\n"
    "> checked them, and they are not part of the participants' threat model."
)


def _about(record, item):
    for key in ("threat", "mitigation"):
        if item.get(key):
            return item[key]
    if item.get("element"):
        return _element_name(record, item["element"])
    return STAGE_TITLES[item["stage"]]


def facilitator_notes(record):
    """Return the facilitator's notes: hints not taken up, then every note."""
    hinted = [
        f"- {STAGE_TITLES[h['stage']]}, {_about(record, h)}: {_text(h['point'])}"
        for h in record["hints"] if not h["takenUp"]
    ]
    not_raised = [
        f"- {STAGE_TITLES[n['stage']]}, {_about(record, n)}: {_text(n['text'])} (not raised in the session)"
        for n in record["notes"] if n["kind"] == "not_raised"
    ]
    questioned = [
        f"- {_about(record, n)}: {_text(n['text'])}"
        for n in record["notes"] if n["kind"] == "questioned_kept"
    ]
    sections = [
        ("## Hinted at, and not taken up", hinted),
        ("## Not raised in the session", not_raised),
        ("## Questioned, and kept", questioned),
    ]
    parts = [f"# {title(record['system'], NOTES)}", NOTES_OPENING]
    for heading, items in sections:
        parts.append(heading)
        parts.append("\n".join(items) if items else "Nothing.")
    return "\n\n".join(parts) + "\n"
