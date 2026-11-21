"""The session record: what a threat modelling session has established so far.

Everything the written model is made from is here, as plain JSON types, because
it is kept in the agent's state and restored with the conversation. The model
that drives STRIDEr changes it only through the tools in tools.py, and the
rules that can be counted are kept here, in code.

The shape and the rules are in specs/008-threat-model-session/data-model.md.

Nothing in this module logs. The record holds what people said and their names.
"""

import copy

STAGES = ("scope", "system", "threats", "rating", "mitigations", "model")
STAGE_STATUSES = ("not_started", "in_progress", "complete", "skipped")

IN_PROGRESS = "in_progress"
FINISHED = "finished"
ABANDONED = "abandoned"

CATEGORIES = (
    "spoofing",
    "tampering",
    "repudiation",
    "information_disclosure",
    "denial_of_service",
    "elevation_of_privilege",
)

ELEMENT_PREFIXES = {
    "component": "C",
    "data_store": "DS",
    "external_party": "EP",
    "data_flow": "F",
}

# Which STRIDE categories normally apply to each kind of element (research.md,
# Decision 9). The coverage table has a cell for each.
APPLIES = {
    "external_party": ("spoofing", "repudiation"),
    "component": CATEGORIES,
    "data_flow": ("tampering", "information_disclosure", "denial_of_service"),
    "data_store": ("tampering", "repudiation", "information_disclosure", "denial_of_service"),
}

LEVELS = ("high", "medium", "low")

# The OWASP Risk Rating Methodology's table: SEVERITY[impact][likelihood].
SEVERITY = {
    "high": {"low": "medium", "medium": "high", "high": "critical"},
    "medium": {"low": "low", "medium": "medium", "high": "high"},
    "low": {"low": "note", "medium": "low", "high": "medium"},
}
SEVERITIES = ("critical", "high", "medium", "low", "note")

DECISIONS = ("mitigate", "accept", "transfer", "avoid")
SCOPE_KINDS = ("included", "excluded", "assumption")
NOTE_KINDS = ("not_raised", "questioned_kept")
FINDING_KINDS = ("differs", "not_mentioned")
CHANGES = ("skip_stage", "finish", "abandon")

# The keys of the agent's state (data-model.md, "What the agent keeps in its state").
KEY_SESSION = "session"
KEY_REPOSITORIES = "repositories"
KEY_LAST_MESSAGE_ID = "lastMessageId"
KEY_LAST_MESSAGE_DONE = "lastMessageDone"
KEY_SESSION_BEFORE = "sessionBefore"

_LISTS = (
    "participants", "joinedAfter", "scope", "elements", "boundaries", "findings",
    "threats", "noneFound", "mitigations", "openQuestions", "hints", "notes",
    "removedAfterNotes",
)


class Refused(Exception):
    """A change the rules do not allow. The message is fit to show the model."""


def _text(value, what, required=True):
    value = value.strip() if isinstance(value, str) else ""
    if required and not value:
        raise Refused(f"{what} is missing.")
    return value


def _one_of(value, allowed, what):
    if value not in allowed:
        raise Refused(f"{what} must be one of: {', '.join(allowed)}.")
    return value


class Record:
    """One session's record. A thin layer of rules over a JSON-safe dict."""

    def __init__(self, data):
        self.data = data

    # --- making and reading ---------------------------------------------------

    @classmethod
    def start(cls, skill, system, speaker, today):
        """Return the record of a session that has just started, in the scope stage."""
        data = {
            "skill": skill,
            "status": IN_PROGRESS,
            "system": _text(system, "The system's name"),
            "startedOn": today,
            "turn": 1,
            "stage": STAGES[0],
            "stages": {stage: "not_started" for stage in STAGES},
            "descriptionComplete": False,
            "pending": None,
            "notesPostedOnTurn": None,
            "endWarned": False,
            "replaceWarnedOnTurn": None,
            "counters": {},
        }
        for name in _LISTS:
            data[name] = []
        data["stages"][STAGES[0]] = "in_progress"
        record = cls(data)
        record.add_person(speaker)
        return record

    @classmethod
    def from_dict(cls, data):
        """Return the record held in data. Raises ValueError when it is not a valid record."""
        if not isinstance(data, dict):
            raise ValueError("not a record")
        for name in _LISTS:
            if not isinstance(data.get(name), list):
                raise ValueError(f"{name} is not a list")
        if data.get("status") not in (IN_PROGRESS, FINISHED, ABANDONED):
            raise ValueError("status")
        if data.get("stage") not in STAGES:
            raise ValueError("stage")
        stages = data.get("stages")
        if not isinstance(stages, dict) or set(stages) != set(STAGES):
            raise ValueError("stages")
        if any(status not in STAGE_STATUSES for status in stages.values()):
            raise ValueError("stage status")
        if not isinstance(data.get("turn"), int) or not isinstance(data.get("counters"), dict):
            raise ValueError("turn or counters")
        if not isinstance(data.get("system"), str) or not isinstance(data.get("skill"), str):
            raise ValueError("system or skill")
        return cls(copy.deepcopy(data))

    def to_dict(self):
        return copy.deepcopy(self.data)

    def __getitem__(self, key):
        return self.data[key]

    @property
    def in_progress(self):
        return self.data["status"] == IN_PROGRESS

    @property
    def ended(self):
        return not self.in_progress

    @property
    def notes_posted(self):
        return self.data["notesPostedOnTurn"] is not None

    def _next_id(self, prefix):
        counters = self.data["counters"]
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}{counters[prefix]}"

    def _find(self, collection, identifier, what):
        for item in self.data[collection]:
            if item["id"] == identifier:
                return item
        raise Refused(f"There is no {what} {identifier}.")

    def element(self, identifier):
        return self._find("elements", identifier, "element")

    def threat(self, identifier):
        return self._find("threats", identifier, "threat")

    # --- people and turns -----------------------------------------------------

    def people(self):
        """Everyone who may be named as having decided something."""
        return self.data["participants"] + self.data["joinedAfter"]

    def add_person(self, name):
        """Add a speaker once: a participant while in progress, joined after once ended."""
        if not name or name in self.people():
            return
        self.data["participants" if self.in_progress else "joinedAfter"].append(name)

    def next_turn(self):
        self.data["turn"] += 1

    # --- scope ----------------------------------------------------------------

    def add_scope_item(self, kind, text):
        item = {
            "id": self._next_id("S"),
            "kind": _one_of(kind, SCOPE_KINDS, "The kind"),
            "text": _text(text, "The text"),
        }
        self.data["scope"].append(item)
        return item

    # --- the system -----------------------------------------------------------

    def add_element(self, kind, name, description=""):
        _one_of(kind, ("component", "data_store", "external_party"), "The kind")
        element = {
            "id": self._next_id(ELEMENT_PREFIXES[kind]),
            "kind": kind,
            "name": _text(name, "The name"),
            "description": _text(description, "", required=False),
        }
        self.data["elements"].append(element)
        return element

    def add_data_flow(self, source, target, data):
        for end in (source, target):
            if self.element(end)["kind"] == "data_flow":
                raise Refused("A data flow runs between two elements that are not data flows.")
        flow = {
            "id": self._next_id(ELEMENT_PREFIXES["data_flow"]),
            "kind": "data_flow",
            "name": f"{source} → {target}",
            "description": "",
            "from": source,
            "to": target,
            "data": _text(data, "What travels on the flow"),
        }
        self.data["elements"].append(flow)
        return flow

    def add_boundary(self, name, inside):
        inside = list(inside or [])
        for identifier in inside:
            if self.element(identifier)["kind"] == "data_flow":
                raise Refused("A trust boundary holds components, data stores and external parties.")
        boundary = {"id": self._next_id("TB"), "name": _text(name, "The name"), "inside": inside}
        self.data["boundaries"].append(boundary)
        return boundary

    def change_element(self, identifier, name="", description=""):
        element = self.element(identifier)
        if element["kind"] == "data_flow":
            raise Refused("A data flow cannot be renamed. Remove it and add it again.")
        if _text(name, "", required=False):
            element["name"] = name.strip()
        if _text(description, "", required=False):
            element["description"] = description.strip()
        return element

    def mark_description_complete(self):
        """Set the flag and return the findings that were being held back."""
        self.data["descriptionComplete"] = True
        held = [finding for finding in self.data["findings"] if not finding["reported"]]
        for finding in held:
            finding["reported"] = True
        return held

    # --- threats --------------------------------------------------------------

    def _touch(self, item):
        if self.notes_posted:
            item["changedAfterNotes"] = True

    def add_threat(self, element, category, description):
        self.element(element)
        threat = {
            "id": self._next_id("T"),
            "element": element,
            "category": _one_of(category, CATEGORIES, "The category"),
            "description": _text(description, "The description"),
            "likelihood": None, "likelihoodReason": "",
            "impact": None, "impactReason": "",
            "severity": None,
            "decision": None, "decisionReason": "",
            "decidedBy": [], "owner": None, "ownerAsked": False,
            "changedAfterNotes": False,
        }
        self._touch(threat)
        self.data["threats"].append(threat)
        self.data["noneFound"] = [
            pair for pair in self.data["noneFound"] if pair != [element, category]
        ]
        return threat

    def none_found(self, element, category):
        self.element(element)
        _one_of(category, CATEGORIES, "The category")
        if any(t["element"] == element and t["category"] == category for t in self.data["threats"]):
            raise Refused("A threat is recorded there. Remove it first if the participants withdraw it.")
        if [element, category] not in self.data["noneFound"]:
            self.data["noneFound"].append([element, category])

    def rate_threat(self, identifier, likelihood, likelihood_reason, impact, impact_reason):
        """Record the participants' rating and return the severity that follows from it."""
        threat = self.threat(identifier)
        _one_of(likelihood, LEVELS, "The likelihood")
        _one_of(impact, LEVELS, "The impact")
        threat["likelihoodReason"] = _text(likelihood_reason, "The reason for the likelihood")
        threat["impactReason"] = _text(impact_reason, "The reason for the impact")
        threat["likelihood"], threat["impact"] = likelihood, impact
        threat["severity"] = SEVERITY[impact][likelihood]
        self._touch(threat)
        return threat["severity"]

    # --- mitigations and decisions --------------------------------------------

    def add_mitigation(self, description, threats, owner=""):
        threats = list(threats or [])
        if not threats:
            raise Refused("A mitigation addresses at least one threat.")
        for identifier in threats:
            self.threat(identifier)
        mitigation = {
            "id": self._next_id("M"),
            "description": _text(description, "The description"),
            "threats": threats,
            "owner": _text(owner, "", required=False) or None,
            "changedAfterNotes": False,
        }
        self._touch(mitigation)
        self.data["mitigations"].append(mitigation)
        return mitigation

    def decide_threat(self, identifier, decision, reason, decided_by, owner=""):
        """Record a decision. Return True when the model should now ask, once, for an owner."""
        threat = self.threat(identifier)
        _one_of(decision, DECISIONS, "The decision")
        reason = _text(reason, "", required=False)
        if decision == "accept" and not reason:
            raise Refused("An accepted threat needs the participants' reason.")
        decided_by = list(decided_by or [])
        if not decided_by:
            raise Refused("Say who decided it.")
        unknown = [name for name in decided_by if name not in self.people()]
        if unknown:
            raise Refused(
                "Not in this session: " + ", ".join(unknown)
                + ". Those who can be named: " + ", ".join(self.people()) + "."
            )
        threat["decision"], threat["decisionReason"], threat["decidedBy"] = decision, reason, decided_by
        owner = _text(owner, "", required=False)
        ask = False
        if owner:
            threat["owner"] = owner
        elif not threat["ownerAsked"]:
            threat["ownerAsked"] = True
            ask = True
        self._touch(threat)
        return ask

    # --- open questions, hints, notes, findings -------------------------------

    def add_open_question(self, text):
        question = {"id": self._next_id("Q"), "text": _text(text, "The question")}
        self.data["openQuestions"].append(question)
        return question

    def give_hint(self, element, point):
        """Record that a hint is being given. At most one for each element in each stage."""
        stage = self.data["stage"]
        element = element or None
        if element:
            self.element(element)
        elif stage != "scope":
            raise Refused("Say which element the hint is about.")
        if any(h["stage"] == stage and h["element"] == element for h in self.data["hints"]):
            raise Refused(
                "A hint has already been given here in this stage. Give no second hint: "
                "record the point with add_note, kind not_raised, and say nothing about it."
            )
        hint = {
            "id": self._next_id("H"), "stage": stage, "element": element,
            "point": _text(point, "The point"), "takenUp": False,
        }
        self.data["hints"].append(hint)
        return hint

    def hint_taken_up(self, identifier):
        self._find("hints", identifier, "hint")["takenUp"] = True

    def add_note(self, kind, text, element=None, threat=None, mitigation=None):
        if element:
            self.element(element)
        if threat:
            self.threat(threat)
        if mitigation:
            self._find("mitigations", mitigation, "mitigation")
        note = {
            "id": self._next_id("N"),
            "kind": _one_of(kind, NOTE_KINDS, "The kind"),
            "stage": self.data["stage"],
            "element": element or None, "threat": threat or None, "mitigation": mitigation or None,
            "text": _text(text, "The text"),
        }
        self.data["notes"].append(note)
        return note

    def add_finding(self, kind, repository, file, fact, files_read):
        """Record what STRIDEr found in a repository file it has read in this session."""
        if file not in files_read:
            raise Refused(f"{file} has not been read from {repository} in this session.")
        finding = {
            "id": self._next_id("R"),
            "kind": _one_of(kind, FINDING_KINDS, "The kind"),
            "repository": repository, "file": file,
            "fact": _text(fact, "The fact"),
            "reported": bool(self.data["descriptionComplete"]),
        }
        self.data["findings"].append(finding)
        return finding

    # --- removing -------------------------------------------------------------

    def remove(self, identifier):
        """Remove one entry. Return a sentence saying what else went with it, or ''."""
        identifier = _text(identifier, "The identifier")
        if identifier.startswith(("H", "N", "R")):
            raise Refused("Hints, notes and findings cannot be removed.")
        if identifier.startswith("TB"):
            return self._drop("boundaries", identifier, "trust boundary")
        if identifier.startswith("S"):
            return self._drop("scope", identifier, "scope item")
        if identifier.startswith("Q"):
            return self._drop("openQuestions", identifier, "open question")
        if identifier.startswith("M"):
            self._drop("mitigations", identifier, "mitigation")
            self._removed_after_notes(identifier)
            return ""
        if identifier.startswith("T"):
            return self._remove_threat(identifier)
        return self._remove_element(identifier)

    def _drop(self, collection, identifier, what):
        self._find(collection, identifier, what)
        self.data[collection] = [item for item in self.data[collection] if item["id"] != identifier]
        return ""

    def _removed_after_notes(self, identifier):
        if self.notes_posted:
            self.data["removedAfterNotes"].append(identifier)

    def _remove_threat(self, identifier):
        self._drop("threats", identifier, "threat")
        self._removed_after_notes(identifier)
        emptied = []
        for mitigation in self.data["mitigations"]:
            if identifier in mitigation["threats"]:
                mitigation["threats"].remove(identifier)
                if not mitigation["threats"]:
                    emptied.append(mitigation["id"])
        for gone in emptied:
            self._drop("mitigations", gone, "mitigation")
            self._removed_after_notes(gone)
        if emptied:
            return "Also removed, because it addressed nothing else: " + ", ".join(emptied) + "."
        return ""

    def _remove_element(self, identifier):
        self.element(identifier)
        flows = [e["id"] for e in self.data["elements"]
                 if e["kind"] == "data_flow" and identifier in (e["from"], e["to"])]
        going = [identifier] + flows
        named = [t["id"] for t in self.data["threats"] if t["element"] in going]
        if named:
            raise Refused("It is named by " + ", ".join(named) + ". Remove those first.")
        self.data["elements"] = [e for e in self.data["elements"] if e["id"] not in going]
        self.data["noneFound"] = [pair for pair in self.data["noneFound"] if pair[0] not in going]
        for boundary in self.data["boundaries"]:
            boundary["inside"] = [inside for inside in boundary["inside"] if inside != identifier]
        return ("Its data flows went with it: " + ", ".join(flows) + ".") if flows else ""

    # --- coverage -------------------------------------------------------------

    def coverage(self, element):
        """Return, for one element, each category's cell: threat ids, or a word."""
        applies = APPLIES[element["kind"]]
        cells = {}
        for category in CATEGORIES:
            threats = [t["id"] for t in self.data["threats"]
                       if t["element"] == element["id"] and t["category"] == category]
            if threats:
                cells[category] = threats
            elif [element["id"], category] in self.data["noneFound"]:
                cells[category] = "none_found"
            elif category in applies:
                cells[category] = "not_considered"
            else:
                cells[category] = "n/a"
        return cells

    def uncovered(self):
        """Return (element id, category) for every cell nobody has looked at."""
        return [
            (element["id"], category)
            for element in self.data["elements"]
            for category, cell in self.coverage(element).items()
            if cell == "not_considered"
        ]

    # --- stages and endings ---------------------------------------------------

    def _enter(self, stage):
        self.data["stage"] = stage
        self.data["stages"][stage] = "in_progress"

    def _leave(self, status):
        """Give the current stage a status and enter the next. Return the next stage, or None."""
        stage = self.data["stage"]
        self.data["stages"][stage] = status
        position = STAGES.index(stage)
        if position + 1 < len(STAGES):
            self._enter(STAGES[position + 1])
            return STAGES[position + 1]
        return None

    def complete_stage(self):
        """Complete the current stage. Never refused.

        Returns what the model needs to say next: the stage entered (None after
        the last), what the threats stage left untouched, and any findings
        released by completing the system stage.
        """
        left = self.data["stage"]
        released = []
        if left == "system" and not self.data["descriptionComplete"]:
            released = self.mark_description_complete()
        return {
            "left": left,
            "entered": self._leave("complete"),
            "uncovered": self.uncovered() if left == "threats" else [],
            "released": released,
        }

    def go_to_stage(self, stage):
        _one_of(stage, STAGES, "The stage")
        self._enter(stage)

    def request_change(self, action):
        """Ask to skip the stage, finish or abandon. Return 'applied' or 'pending'."""
        _one_of(action, CHANGES, "The action")
        if not self.in_progress:
            raise Refused("The session has already ended.")
        if action == "skip_stage" and len(self.data["participants"]) <= 1:
            self._leave("skipped")
            self.data["pending"] = None
            return "applied"
        self.data["pending"] = {
            "action": action, "stage": self.data["stage"], "announcedOnTurn": self.data["turn"],
        }
        return "pending"

    def resolve_change(self, confirmed):
        """Confirm or drop the pending change. Return the action applied, or None when dropped."""
        pending = self.data["pending"]
        if not pending:
            raise Refused("Nothing is pending. If the participants want it, they ask again.")
        if not confirmed:
            self.data["pending"] = None
            return None
        if pending["announcedOnTurn"] >= self.data["turn"]:
            raise Refused(
                "It was only just announced. Wait for the next message, and confirm then "
                "unless that message objects."
            )
        self.data["pending"] = None
        action = pending["action"]
        if action == "skip_stage":
            if self.data["stage"] == pending["stage"]:
                self._leave("skipped")
            else:
                self.data["stages"][pending["stage"]] = "skipped"
            return action
        if action == "finish":
            self.data["stages"]["model"] = "complete"
            self.data["status"] = FINISHED
        else:
            self.data["status"] = ABANDONED
        self.data["notesPostedOnTurn"] = self.data["turn"]
        return action

    def unfinished_stages(self):
        """Return (stage, status) for every stage that is not complete."""
        return [(stage, self.data["stages"][stage]) for stage in STAGES
                if self.data["stages"][stage] != "complete"]


# --- the agent's state --------------------------------------------------------


def load(state):
    """Return the session record in the state, or None. An invalid record counts as none."""
    data = state.get(KEY_SESSION)
    if data is None:
        return None
    try:
        return Record.from_dict(data)
    except ValueError:
        return None


def save(state, record):
    state.set(KEY_SESSION, record.to_dict() if record else None)


def load_repositories(state):
    repositories = state.get(KEY_REPOSITORIES)
    return copy.deepcopy(repositories) if isinstance(repositories, list) else []


def save_repositories(state, repositories):
    state.set(KEY_REPOSITORIES, copy.deepcopy(repositories))


def _restore(state):
    before = state.get(KEY_SESSION_BEFORE)
    if isinstance(before, dict):
        state.set(KEY_SESSION, copy.deepcopy(before.get(KEY_SESSION)))
        state.set(KEY_REPOSITORIES, copy.deepcopy(before.get(KEY_REPOSITORIES) or []))


def begin_message(state, message_id):
    """Prepare the state for one message. Return True when the message is a repeat.

    What a message leads STRIDEr to record is recorded once or not at all
    (FR-063): a message whose handling never finished is undone first, and a
    second request for the same message starts again from before the first.
    """
    if state.get(KEY_LAST_MESSAGE_DONE) is False:
        _restore(state)
    repeat = bool(message_id) and message_id == state.get(KEY_LAST_MESSAGE_ID)
    if repeat:
        _restore(state)
    else:
        state.set(KEY_SESSION_BEFORE, {
            KEY_SESSION: copy.deepcopy(state.get(KEY_SESSION)),
            KEY_REPOSITORIES: copy.deepcopy(state.get(KEY_REPOSITORIES) or []),
        })
        state.set(KEY_LAST_MESSAGE_ID, message_id or None)
    state.set(KEY_LAST_MESSAGE_DONE, False)
    return repeat


def end_message(state):
    """Mark the current message as handled to its end."""
    state.set(KEY_LAST_MESSAGE_DONE, True)
