# Source

This skill was written for this repository, in its own words. It copies no text from any
other skill or document.

Licence: MIT, as the rest of this repository.

The STRIDE categories, the rule for which apply to which kind of element, and the factors
used to rate a threat are other people's methods, restated here. They are credited below.

## What the method comes from

| Part of the skill | Source |
|---|---|
| The six STRIDE categories and the property each threatens | STRIDE was devised at Microsoft. The categories and properties here follow figure 3 of the article below. |
| Which categories apply to which kind of element (`references/threats.md`) | Shawn Hernan, Scott Lambert, Tomasz Ostwald and Adam Shostack, "Uncover Security Design Flaws Using The STRIDE Approach", MSDN Magazine, November 2006, figure 5: <https://learn.microsoft.com/en-us/archive/msdn-magazine/2006/november/uncover-security-design-flaws-using-the-stride-approach> |
| Repudiation asked about for data stores | Adam Shostack, "Experiences Threat Modeling at Microsoft", 2008: "For data stores which are logs, we are concerned with repudiation issues": <https://shostack.org/files/papers/modsec08/Shostack-ModSec08-Experiences-Threat-Modeling-At-Microsoft.pdf>. The 2006 table leaves this cell empty. The skill asks about it for every data store and lets the participants answer "none found" where a store holds no record of who did what. |
| Likelihood, impact and the severity table (`references/rating.md`, and `SEVERITY` in `src/agent/session/record.py`) | OWASP Risk Rating Methodology, by Jeff Williams, OWASP Foundation: <https://owasp.org/www-community/OWASP_Risk_Rating_Methodology>. Licensed CC BY-SA 4.0: <https://creativecommons.org/licenses/by-sa/4.0/>. The sixteen factors are restated as questions, in our own words, and cut down: participants give two judgements, high, medium or low, where the methodology scores each factor from 0 to 9. The severity table is the methodology's. |
| The four decisions about a threat | Adam Shostack's four responses, as given in the OWASP Threat Modeling Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html>. The cheat sheet's "eliminate" is called "avoid" here. |

## Skills it learned from

Nineteen existing skills were looked at before this one was written, and none was adopted
(`specs/008-threat-model-session/research.md`). All but one have the agent name the
threats, rate them and choose the mitigations, which this skill forbids. These gave ideas.
No text was taken from any.

| Skill | Read at | Licence | What was learned |
|---|---|---|---|
| `anthropics/defending-code-reference-harness`, `.claude/skills/threat-model` | `d3bea6b` | Apache-2.0 | The shape of an interview: one question at a time, the owner answers first. |
| `openai/skills`, `skills/.curated/security-threat-model` | `49f948f` | Apache-2.0 | Rules for a subset of Mermaid that always draws, used by the program that lays out the model. |
| `Codeminer42/skills`, `threat-model` | `c8daf5d` | MIT | Opening questions about scope; that an agent accepts no risk, only people do; asking where a control stops. |
| `briiirussell/cybersecurity-skills`, `skills/threat-modeling` | `b198754` | MIT | The four decisions set beside one another, and a model that records who decided. |
| `wshobson/agents`, `stride-analysis-patterns` | `4220308` | MIT | That each category needs its own questions for each kind of element. |
| `jmanico/grim-prompter`, `skills/threat-model` | `2a94457` | MIT | Not inventing a threat to fill a category, and giving a result for every pair. |

## What this skill's coverage was checked against

Checked on 2026-11-22, by reading each page, as FR-062 of spec 008 requires.

| Source | What was compared |
|---|---|
| The MSDN Magazine article above | The categories and properties (figure 3), the table by element (figure 5), the rules for a sensible data flow diagram, the walk through data flows, data stores and processes, and what it says of trust boundaries. |
| Microsoft, "Threats - Microsoft Threat Modeling Tool": <https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats> | The current description of each category. |
| OWASP Threat Modeling Cheat Sheet, above | The four questions, the four steps, the elements of a diagram, the responses to a threat, and the questions for review and validation. |

**Added to the skill because of the check**

- Checks on the description of the system: every data store is written and read, data does
  not move without a component, similar parts are described as one. From the article's
  rules for a sensible diagram.
- Starting the threats stage with the elements a boundary-crossing flow reaches, and not
  being held up by which category a threat belongs to. From the article.
- A review before the model is written: whether the description still matches, whether
  any threat is missing, whether every threat has a decision, whether each mitigation is
  enough. From the cheat sheet's "Review and Validation".
- That transferring a threat leaves something behind, and that a mitigation should be
  something that can be checked. From the cheat sheet.
- That the model should be looked at again when the system changes. From the cheat sheet.

**What those sources cover that this skill leaves out, and why**

| Left out | Why |
|---|---|
| Threat trees and attack patterns: lists of the known ways each threat is carried out against each kind of element or technology. | They name threats. Naming a threat is the participants' work. The skill gives questions that say where to look, not what is there. |
| Research into the known failures of the particular technologies in use. | The same reason. A participant may ask how a technology or a control works, and that is explained. |
| Data flow diagrams at several levels: a context diagram with break-outs. | One level is enough for the size of system a session can cover. A large system is given a narrower scope instead. |
| A numerical ranking of threats, such as likelihood multiplied by impact. | The owner chose the OWASP Risk Rating Methodology's table of high, medium and low. |
| Threats "unique to trust boundaries", as a kind of element of their own. | A trust boundary is not an element here and has no row of its own. Its threats are found through the data flows that cross it, which have their own questions. |
| Limiting who can read the finished model. | The model is posted where the session was held. Who sees it is a matter for that conversation, not for the skill. |
| Checking that mitigations were carried out and worked. | It happens after the session. The model records an owner for each decision. |
| Privacy threats as a separate method, and STRIDE applied to each interaction in place of each element. | Outside STRIDE applied to each element, which is what the owner asked for. |

## Changes

Change this file when the skill takes anything new from elsewhere, and when its coverage
is checked again.
