---
profile: elgora_markdown_bounty_challenge_v1
escrow_amount: "20000000"
submission_deadline: 4102444800
payout_policy: winner_take_all
---

# Audit published protein-binding measurements

## Summary

Produce a reproducible audit of the published protein-binding table and select
a candidate under the analysis rules below.

## Challenge details

### Definitions And Scope

Produce a reproducible audit of the published Adaptyv surface plasmon resonance (SPR) summary from the
2026 Bits to Binders study (Kosonocky et al., DOI
https://doi.org/10.64898/2026.03.03.709355). This bounty purchases historical
analysis of the supplied table, not a new binder, independent replication,
validated affinity estimate, or therapeutic effect. The eligibility rules below
are illustrative analysis choices, not the study's competition rules or a
scientist-approved assay protocol. No new experiments or curve fitting are
required. The cited paper is attribution, not an additional required input.

## What you need to submit (Deliverables)

### Required Outputs And Format

Submit one UTF-8 `result.md`, at most 100,000 bytes, containing the input hash, a row
audit, a candidate summary, and the selected candidate or `none_eligible`.
The row audit covers every row with its eligibility and all failed conditions.
The candidate summary covers every distinct name with its eligibility and
failed candidate conditions, plus the mean `kd` for each eligible candidate.
Rows are identified by their one-based data-record position after the header.
Any readable Markdown arrangement is accepted; no exact headings are required.
No executable is required.

## Inputs, Materials and References

### Access And Known Limitations

Solvers and Guardians use only `b2b_summary.csv`, published in the study authors'
`kosonocky/bits-to-binders` repository as Adaptyv SPR results. It is public over
HTTPS, with no login, signature, payment, or access secret:

https://raw.githubusercontent.com/kosonocky/bits-to-binders/43eeeaf7e6ab629e796c9fe8d20b0ef70a3610d9/scripts/adaptyv/b2b_summary.csv

SHA-256: `625f0af9f9232303520ffac826c73377f0b82160e59f83bb360b7626d0b3ceea`.

The Poster selects that repository and revision as the source of this historical
analysis. The authoritative input is the file with that SHA-256; bytes with any
other hash, including later revisions, are not this input, and a
Solver-provided copy alone is insufficient. The hash identifies the selected
release, not the experiment's authenticity or physical sample identity. Within
the table, link rows by exact `name` and `sequence`; do not claim that this
establishes an independently verified physical chain of custody. No other file
is needed.

## Acceptance Criteria

### Pass/Fail Checks

Parse CSV quoting normally, accepting the UTF-8 byte-order mark before the
header. Numeric fields use base-10 decimal notation, with optional sign and
exponent; trim surrounding ASCII whitespace for numeric parsing only.
Invalid or non-finite numeric text fails the relevant numeric condition.
Preserve other strings; `null`, empty fields, and absent fields are missing.
The columns are `name`, `replicate`, `expression`, `binding`, `kd`, `kon`, `koff`,
`sequence`, `binding_strength`, `confidence`, and `method`.

Mark a row eligible only when all 11 fields are supplied (literal `null` is
allowed in unused `kon`, `koff`, and `binding_strength` fields; other supplied
values in those three fields are ignored), `method` is `SPR`,
`expression` is `medium`, `binding` is `true`, `confidence` is `high`, `sequence`
is nonempty, `replicate` is a positive integer, and `kd` is finite and strictly
positive. Treat `kd` as the published numeric value, without unit conversion or
claiming a new physical estimate. List every failed condition for other rows.
Missing fields never become zero. Published confidence labels are used as-is:
this summary lacks the raw curves and control records needed to re-evaluate
assay quality. Do not infer that missing evidence proves nonbinding.

For each exact `name`, require one identical sequence across all its rows and
unique parsed integer replicate identifiers. A disagreement or duplicate makes that candidate
ineligible. A candidate is eligible only if it has at least two rows and every
row is eligible. This deliberately excludes missing, low-confidence, mixed,
and conflicting evidence rather than choosing the best replicate.

### Scoring And Calculations

For each eligible candidate, calculate the arithmetic mean of its `kd` values
using the published decimals. Sort by ascending mean, breaking exact numeric
ties by ascending case-sensitive candidate name. No rounding precedes selection.
Report means with abs(reported_mean - expected_mean) / expected_mean <=
0.000001; all eligible means are positive. Candidate selection and row labels
must match exactly. Comparison is confined to this published SPR table under
these analysis rules; do not combine predictions, functional assays, or other
experimental conditions with it.

If no candidate is eligible, report `none_eligible` with the row/candidate audit.
That is a valid analysis result, not `no_valid_submission`.

## How is the winner selected?

Among passing Submissions, the active Submission with the lowest
`submission_call_count` wins. `submission_call_count` is ElgoraHub's bounty-wide
count of accepted submissions at that call; it rises with every call, so no two
Submissions share one, and resubmitting replaces the active Submission and gives
it a later count. If none passes, the bounty outcome is `no_valid_submission`.

## Disqualification Conditions

Missing required results, incorrect results under Acceptance Criteria, or
violation of the stated size limit makes a Submission invalid.

## Out Of Scope

New experiments, curve fitting, physical sample verification, and additional
data are outside this historical analysis.

### Allowed Resources And Reuse

Use only the specified input for the analysis. No particular Solver method is
required.

## Evaluation Procedure And Limits

The audit is reproduced from `b2b_summary.csv` alone. The authoritative file
has 304 data records and 47,902 bytes; a file with a different record count is
not the specified input. All 304 records are in scope.

The check runs in three parts: the input source and its row-to-candidate links,
then the eligibility audit, then the calculation and the selected candidate. A
Submission passes only when every required result is correct and within the
stated size limit. Extra explanatory prose is allowed unless it contradicts
those results.
