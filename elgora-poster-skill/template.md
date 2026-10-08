# Elgora Challenge Template

Use the template below, preserving its frontmatter structure. Remove
inapplicable supporting sections rather than filling them with `None`.
Equivalent headings and ordering are allowed. Include conditional detail only
when relevant, and keep requirements consistent across sections.

A `{braced}` span is a prompt addressed to you: replace it with the text it
asks for and remove its braces. Unbraced prose is literal and is published
verbatim on the bounty page. A surviving brace blocks publication.

```markdown
---
profile: elgora_markdown_bounty_challenge_v0
escrow_amount: "{escrow_amount}"
submission_deadline: {submission_deadline}
payout_policy: winner_take_all
---

# {Bounty Title}

## Summary
{Briefly explain the task and desired result.}

## Challenge details
{Explain what the Solver should accomplish and the scope of the task.
Define only terms needed to understand the result.}

## What you need to submit (Deliverables)
{Define the complete set of outputs the Solver must submit. For each deliverable,
state its required content, purpose, and whether it is mandatory or optional.
Explain how related outputs fit together, including which evidence supports
which result or claim.

Specify files, artifacts, reports, datasets or code as relevant to the task.
State any format, organization, naming or size requirements needed to use or
evaluate them. Every required deliverable must be submitted as bytes inside the
Submission: judgment reads only what the sealed package contains, so a link
never stands in for a required artifact. Cite external sources as references
supporting a deliverable, not as the deliverable.

Define Submission completeness here: which outputs and required content must
be present. Refer to Acceptance Criteria for what those outputs must demonstrate,
and to any applicable evidence requirements for their evidentiary support. Leave
implementation choices to the Solver unless a particular method is part of
the bounty's agreed requirements.}

{For datasets or evidence reviews, define the intended coverage and inclusion
and exclusion rules. Explain how missing, duplicate or conflicting records
affect completeness or acceptance where relevant.}

### Deliverable Table (Optional)

Use prose, a list or a table, whichever makes the required outputs clearest.
Adapt the columns to the task.

| Deliverable | Required or optional | Required content | Format or access requirements | Purpose or related criterion |
|---|---|---|---|---|
| {output or artifact} | {required/optional} | {what it must contain} | {applicable requirements} | {what it demonstrates or supports} |

## Inputs, Materials and References
{List required inputs and useful references. Put small inputs directly in the
page, or provide external links to files, datasets, papers and other supporting
material. Distinguish required evaluation inputs from background references;
background reading does not introduce unstated acceptance requirements. Identify
which sources are authoritative for evaluation or verification. Omit this
section only when neither inputs nor references are needed.}

{Where the task depends on materials, facilities or an external verification
service, state what the Poster provides, what the Solver must arrange, who
covers the cost, and when it becomes available. Required external evidence must
be identified and reachable from the page alone: nothing may depend on private
clarification or on an approval given after submission.}

| File or reference | Purpose | Required input or background | Link or access instructions | Version or snapshot, if relevant |
|---|---|---|---|---|
| {file, dataset, paper or other reference} | {why it is useful} | {role in this bounty} | {external link or access instructions} | {governing version or release/observation boundary for required inputs} |

{State the authoritative version or release boundary for each required input,
its content hash where one exists, and the location where it stays reachable for
the whole judging window. A mutable link alone is insufficient when different
contents could change acceptance or ranking; a hash is not mandatory, but a
supplied hash must match. Replacing a specified fixed input requires a new
bounty. For evidence observed later, name the governing source and the
observation boundary; a hash need not exist at publication. State access
restrictions that affect the task. Never include credentials or ask for private
keys, seed phrases, transactions, token approvals, or unrelated signatures.}

## Acceptance Criteria
{Define what each required deliverable must demonstrate to pass, referring to
its required content under Deliverables rather than reproducing the output
checklist. Specify any thresholds, tolerances, comparisons or qualitative
standards needed for that decision. Identify the evidence supporting each
criterion, referring to Evidence, Provenance and Verification where further
detail is needed. Explain how missing, incomplete or conflicting results affect
acceptance where relevant. Make each decision clear enough to apply from the
page alone; put additional comparison conditions in Evaluation Procedure when
needed. Resolve ambiguous terms with the Poster before the review.
Use concrete descriptions or examples where they clarify the expected result.}

{Where relevant, state whether negative or inconclusive results satisfy the
bounty. Distinguish reliable work that finds no effect from evidence that
cannot support a conclusion, and from incomplete or invalid work. Define
acceptance according to the outcome or work the bounty purchases. For
replication or validation, identify the specific finding being tested and what
counts as agreement, disagreement or an inconclusive result.}

### Evidence, Provenance and Verification (When Applicable)
{If acceptance depends on qualifications or independence, define what qualifies,
independence from whom or what, and what evidence establishes those
requirements.}

{Clarify whether the claim concerns a prediction, existing data or new work,
and require evidence appropriate to it. For claims about real-world events or
external sources, define what is independently checkable, the trust
assumptions involved, and what remains unverified. Identify any accepted
verification source, why it is acceptable, and how its evidence connects to the
claim. For new experimental work, explain which records establish that the work
happened, who produced them, and how they connect the tested sample to the
reported result. If acceptance depends on when the work occurred, state whether
existing work qualifies or when new work must occur, and what evidence
establishes that timing.}

{State which underlying data, methods and quality checks are in scope for
verification, what they must show, and how missing or contradictory evidence
affects acceptance. Name any verification source in the page so it is reachable
from the page alone. A Solver assertion, file hash or signature alone does not prove that
claimed work occurred. A hash proves bytes, not origin or validity; a signature
identifies a key, not the truth of its claims. Leave unresolved scientific or
trust decisions with the Poster rather than inventing a protocol or
verification procedure.}

{Where relevant, require Solvers to explain material limitations, uncertainty
and conflicting evidence, and distinguish what the results establish from
what they only suggest.}

{Check required evidence before ranking: a better score cannot compensate for
unsupported claims. Historical-data analysis needs traceable sources and
faithful analysis, not proof of new lab work when it makes no such claim.
Omit this subsection when the deliverable itself supplies all evidence needed
to judge the task.}

### Scoring (When Applicable)
{For a score, define the inputs, calculation and how the result affects
acceptance or ranking. Include units, thresholds, rounding or a worked example
when they clarify that decision. Resolve missing or conflicting results when
they affect acceptance. Refer to rules elsewhere rather than repeating them.
Remove this subsection for a task that does not need it.}

{When applicable, define how partially correct predictions, confidence estimates
and permitted abstentions affect acceptance and ranking. Distinguish a missing
required prediction from unavailable reference evidence.}

## How is the winner selected?
{Define how one winning Submission is selected from those meeting all
acceptance criteria and not disqualified. State the selection method and the
evidence or attributes used to compare eligible Submissions. If using scores,
define the calculation, weights and ranking order, or refer to their definition
above. Numerical scores are optional. For qualitative judging, explain what
makes one eligible Submission better than another. Define terms such as
clarity, usefulness or traceability, state which standards take priority, and
resolve remaining ties. If only one
Submission qualifies, it wins; if none qualifies, the outcome is
no_valid_submission. Keep these rules consistent with acceptance criteria and
the evaluation procedure, and settle them with the Poster before the review.}

## Disqualification Conditions
{State which failures make a Submission ineligible regardless of its score.
Reference the requirements already defined in this bounty rather than creating
a second checklist. Relevant conditions may include a required deliverable
missing from a successfully retrieved and opened Submission, failure of required
evidence to establish the claimed work or sample identity, or material
explicitly prohibited by this bounty. Include only conditions that apply to
this task. A stated condition must be established before it disqualifies a
Submission. A higher score cannot compensate for that failure.}

{If negative or inconclusive results make a Submission ineligible, reference
the applicable acceptance criterion. Do not treat those results as
automatically disqualifying.}

## Out Of Scope
{State relevant exclusions or restrictions. Remove this section if unnecessary.}

## Evaluation Procedure (When Applicable)
{When the bounty requires improvement over a baseline, identify the reference
result, the measure of improvement, and the conditions needed for a fair
comparison. State any minimum improvement required for acceptance and how
uncertainty affects the comparison, where relevant.}

{For predictive benchmarks, distinguish data available during development from
data used for final evaluation. Define any restrictions needed to prevent
evaluation answers from influencing the submitted solution, and what evidence
demonstrates compliance.}

{For forecasts judged against later observations, identify the reference
evidence and who supplies it. State when predictions become final, when outcomes
become available, and what evidence establishes that predictions were fixed
before outcome disclosure. Ensure evidence availability allows judgment within Elgora's
protocol deadlines; the bounty cannot extend them. A timestamp proves ordering,
not that the Solver lacked earlier access to the answers.}

{Where the bounty is for work done a particular way, define the conditions that
define it. This is not only benchmarks and reproductions: an agreed laboratory
procedure, specified equipment or measurement method, a Poster's own model,
dataset or reference point, and which variables are held fixed while others
vary can each be the question being asked. Changing them produces results that
answer a different question or cannot be compared at all.

Specify the models, datasets, reference points, methods, versions and test
conditions — including what stays fixed and what may vary — wherever they
define the task or affect acceptance or ranking. State what evidence must be
submitted to show the conditions were met, and how a deviation or an
inconclusive result affects acceptance. Leave every implementation choice that
does not affect the result open.

Specifying a requirement does not establish that the work was performed or that
its result is scientifically valid; the evidence rules above are what carry
that. Where a scientific choice needs specialist input, leave it with the
Poster and their experts rather than inventing one here.

What stays out is the evaluator's own operation: how it secures execution, what
it installs, what credentials it holds, and what it does when a step fails.
Those belong to the operator and cannot be set from here. Omit this section when
the acceptance and ranking rules already define the evaluation fully.}
```

Out Of Scope and Disqualification Conditions answer different questions. If
doing something should make a Submission ineligible, put it under
Disqualification Conditions. If it is only work the bounty does not pay for,
put it under Out Of Scope. Never put the same thing in both.
