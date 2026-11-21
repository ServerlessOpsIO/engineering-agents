"""The tools the model calls to change the session record.

One Turn is made for each request. Its public methods are the tools; make_tools
wraps the ones the model may be offered. Each tool reads the record from the
agent's state, applies one change through record.py, saves it, and answers with
a short sentence the model acts on.

The rules in contracts/session-tools.md are kept here and in record.py, whatever
the model was told. A refused call answers with the reason and is not an error.

Nothing in this module logs what a tool was given or what it answered: both
hold what people said. A failure is logged by its type alone.
"""

import functools
import logging

from strands import tool

from session import record as rec
from session import render
from session.record import Record, Refused

logger = logging.getLogger("agent")

CHANNEL_THREAD = "channel_thread"
DIRECT_MESSAGE = "direct_message"

START = "start_session"
SESSION_TOOLS = (
    "complete_stage", "go_to_stage", "request_change", "resolve_change", "add_open_question",
    "give_hint", "hint_taken_up", "add_note", "write_model",
)
READING_TOOLS = ("list_repository_files", "read_repository_file")
REPOSITORY_TOOLS = READING_TOOLS + ("hold_finding",)
STAGE_TOOLS = {
    "scope": ("add_scope_item", "remove_item"),
    "system": ("add_element", "add_data_flow", "add_trust_boundary", "change_element",
               "description_complete", "remove_item"),
    "threats": ("add_threat", "none_found", "remove_item"),
    "rating": ("rate_threat", "add_threat"),
    "mitigations": ("add_mitigation", "decide_threat", "rate_threat", "add_threat", "remove_item"),
    "model": (),
}
ALL_STAGE_TOOLS = tuple(dict.fromkeys(name for names in STAGE_TOOLS.values() for name in names))
ALL_TOOLS = (START,) + SESSION_TOOLS + REPOSITORY_TOOLS + ALL_STAGE_TOOLS

SOMETHING_WENT_WRONG = (
    "That could not be done because of a fault, not because of what was asked. "
    "Tell the participants it was not recorded and carry on."
)


def tools_for(record):
    """Return the names of the tools the model is offered for the record as it stands."""
    if record is None:
        return (START,) + READING_TOOLS
    if record.in_progress:
        return SESSION_TOOLS + REPOSITORY_TOOLS + STAGE_TOOLS[record["stage"]]
    return (START,) + REPOSITORY_TOOLS + ALL_STAGE_TOOLS + ("add_open_question", "write_model")


def _answers(method):
    """Make a tool method answer with a sentence whatever happens inside it."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        self.tool_calls += 1
        try:
            return method(self, *args, **kwargs)
        except Refused as refusal:
            return f"Not done. {refusal}"
        except Exception as error:  # A fault must not cost the reply, or reach a log with its text.
            logger.error("Tool %s failed: %s", method.__name__, type(error).__name__)
            return SOMETHING_WENT_WRONG
    return wrapper


def _changes(method):
    """Run a tool method against the session record and save what it did."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        session = rec.load(self.state)
        if session is None:
            raise Refused("There is no session. Start one first.")
        answer = method(self, session, *args, **kwargs)
        rec.save(self.state, session)
        return answer
    wrapper.__signature__ = _without_session(method)
    return wrapper


def _without_session(method):
    import inspect
    signature = inspect.signature(method)
    parameters = [p for name, p in signature.parameters.items() if name != "session"]
    return signature.replace(parameters=parameters)


def _recorded(what):
    return f"Recorded as {what} Say this back to the participants in one line, with the identifier."


class Turn:
    """What one request needs to run the tools: the state, who is speaking, and what to attach."""

    def __init__(self, state, speaker, conversation_type=DIRECT_MESSAGE, thread_ends_at=None,
                 today=None, skill="stride-threat-model"):
        self.state = state
        self.speaker = speaker
        self.conversation_type = conversation_type
        self.thread_ends_at = thread_ends_at
        self.today = today
        self.skill = skill
        self.documents = []
        self.tool_calls = 0

    # --- documents ------------------------------------------------------------

    def _attach(self, kind, markdown, system):
        name = render.filename(system, kind)
        self.documents = [d for d in self.documents if d["filename"] != name]
        self.documents.append({
            "filename": name, "title": render.title(system, kind), "markdown": markdown,
        })

    def _attach_documents(self, session, notes):
        repositories = rec.load_repositories(self.state)
        self._attach(render.MODEL, render.written_model(session, repositories, self.today), session["system"])
        if notes:
            self._attach(render.NOTES, render.facilitator_notes(session), session["system"])

    # --- starting -------------------------------------------------------------

    @_answers
    def start_session(self, system: str) -> str:
        """Start a threat modelling session on a system. Use only when someone asks for one.

        Args:
            system: The name of the system to be modelled, as the person gave it.
        """
        last = rec.load(self.state)
        if last and last.in_progress:
            raise Refused(
                f"A session on \"{last['system']}\" is in progress. Ask whether to continue it "
                "or abandon it."
            )
        if last and last["replaceWarnedOnTurn"] in (None, last["turn"]):
            last.data["replaceWarnedOnTurn"] = last["turn"]
            rec.save(self.state, last)
            raise Refused(
                f"The session on \"{last['system']}\" has ended. Tell them that starting a new one "
                "replaces it: it can then no longer be changed or asked for, though its files "
                "stay in Slack. If they still want to, call start_session again on their next message."
            )

        session = Record.start(self.skill, system, self.speaker, self.today)
        rec.save(self.state, session)
        repositories = rec.load_repositories(self.state)
        for repository in repositories:
            repository["filesRead"] = []
        rec.save_repositories(self.state, repositories)

        points = [
            "the six stages: scope, system, threats, rating, mitigations and decisions, the written model",
            "the participants do the work and you facilitate: you will not name threats, rate "
            "them or choose what to do",
            "you keep notes on what was missed, posted with the model when the session ends",
        ]
        if self.conversation_type == CHANNEL_THREAD:
            points += [
                "you may stay quiet when they talk among themselves, and a mention always gets a reply",
                "you see only what full members of the workspace write",
            ]
            if self.thread_ends_at:
                points.append(f"this thread stops being answered at {self.thread_ends_at} (UTC), "
                              "so the session must finish before then")
        return (
            f"Session started on \"{session['system']}\". Give the opening now, in about six "
            "sentences, covering: " + "; ".join(points) + ". Then name the scope stage and ask "
            "its first question."
        )

    # --- moving through the session -------------------------------------------

    @_answers
    @_changes
    def complete_stage(self, session) -> str:
        """Mark the current stage complete and enter the next. Use when the participants have nothing more to add to it."""
        done = session.complete_stage()
        parts = [f"The {done['left']} stage is complete."]
        if done["uncovered"]:
            by_element = {}
            for element, category in done["uncovered"]:
                by_element.setdefault(element, []).append(category.replace("_", " "))
            listed = "; ".join(f"{e}: {', '.join(c)}" for e, c in by_element.items())
            parts.append(
                f"Not looked at: {listed}. Say once that these will show as \"Not considered\" "
                "and that they can go back. This is not a hint; name no threat."
            )
        if done["released"]:
            parts.append(self._findings_text(done["released"]))
        if done["entered"]:
            parts.append(f"Now in the {done['entered']} stage. Name it and ask its first question.")
        else:
            parts.append("That was the last stage. Ask whether the participants want to finish.")
        return " ".join(parts)

    @_answers
    @_changes
    def go_to_stage(self, session, stage: str) -> str:
        """Go to another stage, earlier or later, without completing or skipping the current one.

        Args:
            stage: One of scope, system, threats, rating, mitigations, model.
        """
        session.go_to_stage(stage)
        return f"Now in the {stage} stage. Say so."

    @_answers
    @_changes
    def request_change(self, session, action: str) -> str:
        """Record that a participant asked to skip the current stage, finish the session or abandon it.

        Args:
            action: One of skip_stage, finish, abandon.
        """
        if session.request_change(action) == "applied":
            return f"Skipped. Now in the {session['stage']} stage. Name it and ask its first question."
        if action == "skip_stage":
            return (
                "Pending. Tell the participants the stage is about to be skipped. On the next "
                "message call resolve_change, confirmed true unless that message objects."
            )
        return (
            "Pending. Tell the participants that the written model and your notes are about to "
            "be posted and that changes made afterwards will be marked. On the next message "
            "call resolve_change, confirmed true unless that message objects."
        )

    @_answers
    @_changes
    def resolve_change(self, session, confirmed: bool) -> str:
        """Confirm or drop the change that was announced. Use on the message after the announcement.

        Args:
            confirmed: True when the message does not object. False when it objects, asks to wait or questions it.
        """
        action = session.resolve_change(confirmed)
        if action is None:
            return "Dropped. Carry on with the session. If they ask again later, announce it afresh."
        if action == "skip_stage":
            return f"Skipped. Now in the {session['stage']} stage. Name it and ask its first question."
        self._attach_documents(session, notes=True)
        word = "finished" if action == "finish" else "abandoned"
        return (
            f"The session is {word}. The written model and the facilitator's notes are attached "
            "to this reply as files. Say so in a sentence or two. Do not write them out."
        )

    @_answers
    @_changes
    def write_model(self, session) -> str:
        """Attach the written model to this reply as a file. Use when asked for the model."""
        self._attach_documents(session, notes=session.ended)
        if session.ended:
            return ("The written model and the facilitator's notes are attached as files. "
                    "Say so. Do not write them out.")
        return ("The written model as it stands is attached as a file, with unfinished stages "
                "marked. Say so. Do not write it out.")

    @_answers
    @_changes
    def add_open_question(self, session, text: str) -> str:
        """Record something the participants could not answer or agree on.

        Args:
            text: The question, in their words.
        """
        question = session.add_open_question(text)
        return _recorded(f"{question['id']}, an open question: {question['text']}.")

    # --- hints and notes ------------------------------------------------------

    @_answers
    @_changes
    def give_hint(self, session, point: str, element: str = "") -> str:
        """Record that you are about to give a hint. Call this before giving it.

        Args:
            point: What the participants have missed. For your notes, not for saying.
            element: The element it is about. Leave empty in the scope stage.
        """
        hint = session.give_hint(element, point)
        return (
            f"Noted as {hint['id']}. Now give the hint: point at the area and DO NOT name the "
            "threat. If they take it up, call hint_taken_up."
        )

    @_answers
    @_changes
    def hint_taken_up(self, session, hint: str) -> str:
        """Record that the participants raised the point after a hint.

        Args:
            hint: The hint's identifier, such as H1.
        """
        session.hint_taken_up(hint)
        return "Noted."

    @_answers
    @_changes
    def add_note(self, session, kind: str, text: str, element: str = "", threat: str = "",
                 mitigation: str = "") -> str:
        """Add to your facilitator's notes. Say nothing about it to the participants.

        Args:
            kind: not_raised for a missed point you could not hint at; questioned_kept for a rating or mitigation you questioned and they kept.
            text: The point, or what you questioned.
            element: The element it is about, if any.
            threat: The threat it is about, if any.
            mitigation: The mitigation it is about, if any.
        """
        session.add_note(kind, text, element or None, threat or None, mitigation or None)
        return "Noted. Do not mention it."

    # --- scope ----------------------------------------------------------------

    @_answers
    @_changes
    def add_scope_item(self, session, kind: str, text: str) -> str:
        """Record one thing about the scope.

        Args:
            kind: included, excluded or assumption.
            text: What the participants said.
        """
        item = session.add_scope_item(kind, text)
        return _recorded(f"{item['id']}, {item['kind']}: {item['text']}.")

    @_answers
    @_changes
    def remove_item(self, session, id: str) -> str:
        """Remove something the participants withdraw.

        Args:
            id: The identifier of a scope item, element, trust boundary, threat, mitigation or open question.
        """
        also = session.remove(id)
        return f"Removed {id}. {also}".strip() + " Say so."

    # --- the system -----------------------------------------------------------

    @_answers
    @_changes
    def add_element(self, session, kind: str, name: str, description: str = "") -> str:
        """Record a part of the system the participants described.

        Args:
            kind: component, data_store or external_party.
            name: Its name.
            description: What it does, if they said.
        """
        element = session.add_element(kind, name, description)
        return _recorded(f"{element['id']}, a {kind.replace('_', ' ')}: {element['name']}.")

    @_answers
    @_changes
    def add_data_flow(self, session, source: str, target: str, data: str) -> str:
        """Record data moving from one element to another.

        Args:
            source: The identifier of the element the data leaves.
            target: The identifier of the element the data reaches.
            data: What travels.
        """
        flow = session.add_data_flow(source, target, data)
        return _recorded(f"{flow['id']}, a data flow from {source} to {target}: {flow['data']}.")

    @_answers
    @_changes
    def add_trust_boundary(self, session, name: str, inside: list[str]) -> str:
        """Record a trust boundary the participants described.

        Args:
            name: Its name.
            inside: The identifiers of the elements inside it.
        """
        boundary = session.add_boundary(name, inside)
        holds = ", ".join(boundary["inside"]) or "nothing yet"
        return _recorded(f"{boundary['id']}, a trust boundary: {boundary['name']}, holding {holds}.")

    @_answers
    @_changes
    def change_element(self, session, id: str, name: str = "", description: str = "") -> str:
        """Change an element's name or description when a participant corrects it.

        Args:
            id: The element's identifier.
            name: The new name, or empty to keep it.
            description: The new description, or empty to keep it.
        """
        element = session.change_element(id, name, description)
        return _recorded(f"{element['id']}: {element['name']}.")

    def _findings_text(self, findings):
        if not findings:
            return "Nothing from a repository was being held back."
        listed = " ".join(
            f"[{f['kind'].replace('_', ' ')}] {f['repository']}/{f['file']}: {f['fact']}"
            for f in findings
        )
        return (
            "Report these repository findings now, together, as facts, naming each file, and "
            "ask the participants which is right or whether a part belongs in the model. Add "
            f"nothing to the record until they say so. {listed}"
        )

    @_answers
    @_changes
    def description_complete(self, session) -> str:
        """Record that the participants have said their description of the system is complete."""
        return "Noted. " + self._findings_text(session.mark_description_complete())

    # --- threats, ratings, mitigations, decisions -----------------------------

    @_answers
    @_changes
    def add_threat(self, session, element: str, category: str, description: str) -> str:
        """Record a threat a participant named. Never one of your own.

        Args:
            element: The identifier of the element it affects.
            category: spoofing, tampering, repudiation, information_disclosure, denial_of_service or elevation_of_privilege.
            description: The threat, in the participant's words, shortened if need be.
        """
        threat = session.add_threat(element, category, description)
        return _recorded(
            f"{threat['id']}: {category.replace('_', ' ')} on {element}, {threat['description']}."
        )

    @_answers
    @_changes
    def none_found(self, session, element: str, category: str) -> str:
        """Record that the participants looked at a category for an element and found no threat.

        Args:
            element: The element's identifier.
            category: The STRIDE category they looked at.
        """
        session.none_found(element, category)
        return f"Recorded none found for {category.replace('_', ' ')} on {element}."

    @_answers
    @_changes
    def rate_threat(self, session, threat: str, likelihood: str, likelihood_reason: str,
                    impact: str, impact_reason: str) -> str:
        """Record the participants' rating of a threat. The severity is worked out for you.

        Args:
            threat: The threat's identifier.
            likelihood: high, medium or low, as the participants said.
            likelihood_reason: Their reason.
            impact: high, medium or low, as the participants said.
            impact_reason: Their reason.
        """
        severity = session.rate_threat(threat, likelihood, likelihood_reason, impact, impact_reason)
        return _recorded(
            f"{threat}: likelihood {likelihood}, impact {impact}. The severity that follows "
            f"from the table is {severity}. State it."
        )

    @_answers
    @_changes
    def add_mitigation(self, session, description: str, threats: list[str], owner: str = "") -> str:
        """Record a mitigation a participant proposed. Never one of your own.

        Args:
            description: What they will do.
            threats: The identifiers of the threats it addresses.
            owner: Who is responsible, if they said. May be empty.
        """
        mitigation = session.add_mitigation(description, threats, owner)
        return _recorded(
            f"{mitigation['id']}: {mitigation['description']}, addressing "
            f"{', '.join(mitigation['threats'])}, owner {mitigation['owner'] or 'none named'}."
        )

    @_answers
    @_changes
    def decide_threat(self, session, threat: str, decision: str, decided_by: list[str],
                      reason: str = "", owner: str = "") -> str:
        """Record the participants' decision about a threat. Never your own.

        Args:
            threat: The threat's identifier.
            decision: mitigate, accept, transfer or avoid.
            decided_by: The names of whoever said it, and of everyone who agreed.
            reason: Their reason. Required when the decision is accept.
            owner: Who is responsible for carrying it out. May be empty.
        """
        ask = session.decide_threat(threat, decision, reason, decided_by, owner)
        said = _recorded(
            f"{threat}: {decision}, decided by {', '.join(decided_by)}, "
            f"owner {owner.strip() or 'none named'}."
        )
        if ask:
            said += " No owner was named: ask once who is responsible. If none is named, leave it."
        return said


def make_tools(turn, extra=None):
    """Return every tool as {name: tool}, bound to one request's Turn.

    extra adds tools kept elsewhere, such as the repository tools, by name.
    """
    tools = {name: tool(getattr(turn, name)) for name in ALL_TOOLS if hasattr(turn, name)}
    for name, function in (extra or {}).items():
        tools[name] = tool(function)
    return tools
