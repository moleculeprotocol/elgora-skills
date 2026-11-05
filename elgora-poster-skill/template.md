# Elgora Challenge Template

Use the five core sections below. Add a supporting section only when it resolves
an acceptance or ranking decision for this bounty; omit it otherwise. Keep the
five core headings as written; order supporting sections as reads best. Tables
are optional.

Replace every `{braced}` prompt with the agreed content and remove the braces.
Unbraced text inside the draft block is published as written; remove drafting
instructions. Read the drafting rules in `SKILL.md`.

```markdown
---
profile: elgora_markdown_bounty_challenge_v1
escrow_amount: "{escrow_amount}"
submission_deadline: {submission_deadline}
payout_policy: winner_take_all
---

# {Bounty Title}

## Summary
{What is the Poster purchasing? State the task and desired result briefly.}

## Challenge details
{Explain the task, scope and definitions needed to understand the result.
Preserve any agreed method or conditions that define the work; leave other
implementation choices to the Solver.}

## What you need to submit (Deliverables)
{Name the files or folders and the content needed to judge the result. State
which are required and which are optional. Specify a format or layout only
where it matters. Describe paths relative to the Submission root, not packaging
or compression. Required deliverables must be submitted as bytes; a link to
code, data or a report cannot replace the deliverable. External inputs and
citations may be linked.}

## Acceptance Criteria
{State the observable conditions that make a Submission valid. Keep gates to
what the Poster would refuse to pay without. For each threshold, state its
source; for each claim, identify the evidence that supports the decision.
Define relevant tolerances and how missing or conflicting evidence affects
acceptance. Do not repeat the deliverables checklist. Where it matters, decide
whether a negative or inconclusive result fulfils the requested work.}

## How is the winner selected?
{Explain how valid Submissions rank and how every remaining tie is broken.
Define comparison terms, priorities and any calculation, including which value
is used if a Submission supplies several. Numerical scoring is optional.
Select exactly one winner whenever any Submission qualifies; otherwise the
outcome is no_valid_submission. Confirm the ranking and tie-break with the
Poster.}
```

## Supporting sections — only where needed

Insert relevant sections into the draft with `##` headings, in whichever order
reads best.
These prompts are questions to resolve, not requirements to impose on every
bounty. Do not leave empty sections or instructional text in the published page.

### Inputs, Materials and References

An input labelled optional must not be necessary for required work.
Identify required inputs separately from background reading. State where they
are available and which version or observation boundary governs judgment.
Pin the content when different contents could change the outcome; include a
hash when available, and verify it. For later evidence, identify the governing
source and when it becomes available within the protocol's judging window.
Clarify who provides any required materials or access and who pays for them.
No essential decision may depend on private clarification after publication.

For a fixed external file, this optional row illustrates the information to
resolve. Replace every placeholder with verified values or remove the row
before publication; never invent a hash.

| Input | Access and selected version | SHA-256 |
| --- | --- | --- |
| `{filename}` | `{URL or access method for the selected version}` | `{verified file hash}` |

Bytes with a different hash are not the selected input.

### Evidence, Provenance and Verification

State what evidence supports each material claim, what can be independently
checked, the trust assumptions and what remains unverified. A hash establishes
bytes, not truth; a signature identifies a key, not the validity of its claims.
Where acceptance depends on origin, timing, qualifications or independence,
define the requirement and how evidence establishes it. For new work, connect
the reported result to the work and sample claimed. Do not require proof of new
work when the task is analysis of existing data. Leave unresolved subject-matter
or trust choices with the Poster and their experts.

### Evaluation Procedure

Define only conditions needed to evaluate or compare the requested results:
authoritative inputs, methods, versions, what stays fixed, what may vary, and
any metric, units, rounding or tolerance. State the evidence for compliance
and the effect of deviations or inconclusive results. For a benchmark, identify
the baseline and any separation of development data from evaluation answers.
For later outcomes, define when predictions become final and how that ordering
is established. A timestamp proves ordering, not that the Solver lacked earlier
access to the answers. State what the result demonstrates and its limits.

Describe the judgment, not Guardian operations: no sandbox configuration,
credentials, retries or handling of unavailable sources. A method can be part
of the purchased work without prescribing how a Guardian operates.

### Disqualification Conditions

Include only additional failures that make a Submission ineligible regardless
of rank. Refer to an existing acceptance requirement instead of repeating it.
Do not disqualify a Solver for a platform retrieval or decryption failure.

### Out Of Scope

State relevant work the bounty does not purchase. If an action instead makes a
Submission ineligible, put that rule under acceptance or disqualification.

## If the Poster chooses earliest Submission as the final tie-break

Use these sentences unchanged:

> Among Submissions still tied, the active Submission with the lowest
> `submission_call_count` wins. `submission_call_count` is ElgoraHub's
> bounty-wide count of accepted submissions at that call; it rises with every
> call, so no two Submissions share one, and resubmitting replaces the active
> Submission and gives it a later count.
