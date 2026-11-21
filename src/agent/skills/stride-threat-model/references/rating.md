# Stage: rating

**Aim**: the participants give each threat a likelihood and an impact, each **high**,
**medium** or **low**, with a reason for each. The severity follows from the two and is
worked out by the `rate_threat` tool. State the severity it returns. DO NOT give a
likelihood, an impact or a severity of your own.

The method is the OWASP Risk Rating Methodology, cut down to two judgements. Its factors
are used here as questions that help participants reason. Ask about a factor only when
the participants have not already addressed it, and one at a time.

## Likelihood: how likely is it that this happens?

**About whoever would do it**

- Skill: how much skill would it take?
- Motive: what would they gain, and is it worth their while?
- Opportunity: what access or resources would they need first?
- Size: how many people or systems are in a position to try?

**About the weakness**

- Ease of discovery: how easy is it to find?
- Ease of exploit: once found, how easy is it to use?
- Awareness: how well known is this kind of weakness?
- Detection: would anyone notice an attempt, and how soon?

## Impact: how bad is it if it does?

**Technical**

- Confidentiality: how much data could be seen, and how sensitive is it?
- Integrity: how much could be changed, and how badly?
- Availability: how much of the service could be lost, and for how long?
- Accountability: could what was done be traced to whoever did it?

**To the business**

- Financial: what would it cost?
- Reputation: who would find out, and what would they think?
- Compliance: what rule or contract would it break?
- Privacy: how many people's personal data would be exposed?

Use the worst realistic case for whoever would do it.

## Recording

Call `rate_threat` with the participants' two values and their reason for each, in their
words. Read back the rating and the severity the tool returns.

## Doubts

When a rating contradicts something said earlier in the session, or there is any other
doubt, raise it as a question, once, without giving a value: "Earlier it was said that
anyone on the internet can reach this. How does that fit with a low likelihood?" If the
participants keep the rating, call `add_note` with kind `questioned_kept`.

## Before closing the stage

Every threat should have a rating or the participants' word that it stays unrated. Then
call `complete_stage`.
