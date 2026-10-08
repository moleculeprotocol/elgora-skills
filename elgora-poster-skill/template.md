# Elgora V0 Challenge Template

Copy the block below into `bounty_challenge.md`. Keep its frontmatter
structure. Equivalent headings and ordering are allowed.

A `{braced}` span is a question for you and the Poster: replace it with the
answer and remove the braces. Unbraced text is published as written. A
surviving brace blocks publication.

Keep simple tasks brief. Define each requirement once and refer to it
elsewhere. The page defines what a Solver submits and how a Guardian judges it.
It never teaches API calls, transactions, encryption or wallet steps.

```markdown
---
profile: elgora_markdown_bounty_challenge_v0
escrow_amount: "{escrow amount in USDC smallest units, e.g. 1 USDC = 1000000}"
submission_deadline: {deadline as Unix seconds, UTC}
payout_policy: winner_take_all
---

# {Bounty Title}

## Summary
{What is the task, and what result does the Poster want?}

## Challenge details
{What must the Solver accomplish, and within what scope? Define only the terms
needed to understand the result.}

## What you need to submit (Deliverables)
{Which outputs must be submitted? For each: its required content, its purpose,
and whether it is required or optional. Which evidence supports which claim?
State formats, naming or size only where judgment needs them. Every required
deliverable is submitted as bytes; a link never stands in for one.}

## Acceptance Criteria
{What must each required deliverable demonstrate to pass? Give thresholds,
tolerances or qualitative standards. How do missing, incomplete, conflicting,
negative or inconclusive results affect acceptance? Each decision must be clear
from the page alone.}

## How is the winner selected?
{How is one winner chosen from the Submissions that pass and are not
disqualified? What is compared, in what order of priority, and how are ties
broken? If only one Submission qualifies, it wins; if none does, the outcome is
no_valid_submission.}

## Disqualification Conditions
{Which failures make a Submission ineligible whatever its score? Refer to
requirements already stated instead of repeating them. Include only conditions
that apply to this task.}
```

## Optional Sections

Add one only when the bounty needs it. Remove it rather than writing `None`.

| Section | Add it when | Example |
| --- | --- | --- |
| `## Inputs, Materials and References` | The task needs inputs or references. | Both examples |
| `### Evidence, Provenance and Verification` | Acceptance depends on proving where data came from, who did the work, or when. | — |
| `### Scoring` | A number decides acceptance or ranking. | `protein_binding.md` |
| `## Out Of Scope` | Exclusions would otherwise be unclear. | Both examples |
| `## Evaluation Procedure` | A baseline, benchmark, forecast or fixed method defines the task. | `protein_binding.md` |

Rules for those sections:

- **Inputs.** Separate required inputs from background reading. For each
  required input, name the authoritative version, its hash where one exists,
  and where it stays reachable for the whole judging window. Never include
  credentials.
- **Evidence.** A hash proves bytes, not origin. A signature identifies a key,
  not the truth of a claim. A better score never makes up for unsupported
  evidence.
- **Out Of Scope.** If doing something should make a Submission ineligible,
  put it under Disqualification Conditions. If it is only work the bounty does
  not pay for, put it under Out Of Scope. Never put the same thing in both.
- **Evaluation Procedure.** State what stays fixed, what may vary, and what
  evidence shows the conditions were met. Leave out how the evaluator runs:
  sandboxing, installs, credentials, retries.

The examples use a distant sentinel deadline. Replace every example value
before publishing.
