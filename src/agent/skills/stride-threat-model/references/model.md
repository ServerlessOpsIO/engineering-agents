# Stage: the written model

**Aim**: the participants receive the written model.

The model is laid out by the `write_model` tool from the session record. DO NOT write it
out in a reply.

## Reviewing before the model is written

A threat model ends by asking whether the job was done well enough. Ask these, one at a
time, and let the participants answer. Go back to a stage with `go_to_stage` when an
answer calls for it.

1. Does the description of the system still match the system, now that it has been
   looked at closely?
2. Is there any threat anyone has thought of since that is not recorded?
3. Does every threat have a decision? The record shows which do not.
4. For the threats to be mitigated: is each mitigation enough, in the participants' view,
   to bring the risk down to what they can live with?
5. Who else should read this model before it is relied on?

A model describes the system as it is today. Say once that it should be looked at again
when the system changes.

## What to do

1. Say what the model will contain and ask whether anything should change first.
2. Asked for the model, call `write_model`. It arrives as a file.
3. When the participants say the session is finished, follow "Skipping, finishing and
   abandoning": call `request_change` with `finish`, give the warning, and on the next
   message call `resolve_change`. The model and the facilitator's notes are then posted.
4. When unsure whether they have said the session is finished, ask.

## After the session has ended

Changes can still be made, each marked as made after the notes. Asking for the model again
brings the model and the notes.
