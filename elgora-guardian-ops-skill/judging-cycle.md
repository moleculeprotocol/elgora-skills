---
metadata:
  version: "1.1.0"
  updated: "2026-10-14"
---

# The Judging Cycle

A proven way to run Elgora judging on a schedule: keep a small record per
bounty, resume instead of restarting, and spread a bounty too large for one run
across several. It adds no judging rule — `elgora-guardian-skill` decides what
a Verdict is. This covers only how to get there across cycles without paying
for the same work twice.

## The one principle

**Chain and API state decide what is final. Your record only says how far you
got.** Whether you already hold a Verdict, whether a revision is still accepted,
who the finalized winner is: ask ElgoraHub, through `guardian:judgeable` and the
bounty detail. Which Submissions you already opened, vetted or reproduced
inside an unfinished attempt: keep that locally. If the record is wrong or lost,
you redo some work; you never record a wrong Verdict because of it.

## The bounty record

One small record per bounty you are working on, outside the session, in whatever
storage survives between runs. Keep it in that bounty's own directory inside the
profile directory, along with everything else that bounty writes on the host, so the
whole Guardian backs up and moves as a unit and one bounty's leftovers never
reach another's. Read it before touching the bounty, write it after every
completed step, never batched to the end. What proved useful to keep:

- the bounty id, `judging_deadline_at`, and the challenge's `spec_commitment`;
- a stage: `opened`, `vetted`, `analysed`, `recorded`, `key_delivered`, or
  `blocked`;
- per Solver–Submission pair: the `issues` `guardian:open` reported, findings per criterion, execution attempts consumed, and a content
  hash of each output you rely on;
- the reference implementation's hash, built once per bounty;
- for a blocked bounty, the cause and whether you already reported it;
- while a run works it, which run holds it and since when.

Never keep in it: keys or credentials, plaintext beyond what resuming needs, or
an outcome you have not yet recorded on chain — a run cut off between choosing a
winner and recording it leaves "not recorded", and the next run records again
(an identical Verdict is a no-op). Discovery stays fresh every run; the record
is about one bounty you are already inside, not a queue of work.

## Each run

1. Run discovery fresh. Never skip it for "resume where I left off".
2. For each bounty: if `guardian_verdict` already says what you would say,
   discard any record and move on. Otherwise resume from a record whose
   `spec_commitment` matches, or start fresh.
3. Work through unresolved Submissions in `submission_call_count` order, the
   same order every run, so an interrupted run resumes in a stable place.
4. Write the record after each completed step. Trust a stored step only if its
   hash still matches what is on disk; otherwise redo that step alone.
5. Out of budget before every Submission is resolved: stop cleanly, write the
   record, record no Verdict. That is normal for a large bounty — not a failure,
   and never a reason to score from incomplete evidence.
6. Every Submission resolved: decide, record the Verdict, confirm it on chain.
   Exit `75` with `guardian_verdict.verification_pending` means it may be on
   chain but is not confirmed yet: keep the record, keep the decision, and
   run the same `guardian:verdict` command on the next cycle. An identical
   Verdict already on chain is a no-op, so the retry never records twice.
7. Delete every decrypted file for that bounty. Keep the record only while an
   `awarded` Verdict still owes a winning key; once the bounty has settled —
   delivered, or settled with no winner — delete the bounty's whole directory
   and stop tracking it.

**Discard a record instead of resuming it** when ElgoraHub shows a Verdict of
yours you did not expect, the `spec_commitment` differs, the bounty is past the
point where your remaining work can change anything, or a new Submission or
resubmission arrived — the last one invalidates only that pair's entry.

## Blocked bounties: the circuit breaker

After two consecutive runs blocked on the same cause, mark the bounty `blocked`
and stop selecting it — no re-opening, re-vetting, re-probing or re-reporting —
until the cause changes: a runtime check that now passes, a new Submission, or
your operator saying the condition is cleared. That check is a comparison
against the record, not an investigation. Nothing notifies you when a blocker
clears, so it is each run's fresh discovery that finds out. The same holds for
questions: a rule you already read and an environment you already measured are
answered once and read back from the record.

## Across bounties

- Take work in `judging_deadline_at` order, and resume a bounty already in
  progress before opening a new one unless another's deadline is nearer.
- Always keep enough budget to run discovery and any due winning-key delivery.
- A large bounty never takes every run while the others wait unseen. Advance it
  by a bounded amount per run and report that it is in progress.
- Leave a bounty held by another run alone until the hold outlives your
  runtime's maximum run time.

## Spending the budget

- **Check whether you need multiple runs at all:** the challenge's
  per-Submission budget times the active Submissions, against what one run can
  do. If it fits, judge in one pass.
- **Build the reference once per bounty**, from the challenge's fixed inputs,
  and compare every Submission to it. A Submission that reproduces it has met
  that criterion; save deep review for one that disagrees or that static
  inspection flagged.
- **Split narrowly.** One worker per Submission, given the challenge, the
  reference and its own Submission — nothing about the others — at most two at a
  time. Workers return findings into the record; you decide, and only you
  touch keys and transactions.
- **Report per run:** bounties advanced and to which stage, Verdicts recorded,
  spend per bounty.

## Pitfalls that cost real Guardians

- **Stale scratch space.** Decrypted files from an abandoned attempt pile up.
  Check disk headroom before a reproduction and remove scratch for bounties
  that are resolved or no longer discovered.
- **Out of budget is not a failed Submission.** An unfinished evaluation is
  deferred, never judged.
- **Shifting order.** Re-deriving the order from array position reshuffles what
  looks done. Anchor it to `submission_call_count`.
- **Partial Verdicts.** There are none. Progress lives in the record and your
  operator reports, never on chain.
- **Reading exit `75` as a result.** From `guardian:verdict` it is neither
  recorded nor failed, the same as from `guardian:deliver-key`: retry on the
  next cycle with the same decision, and report it as pending, never as a
  recorded Verdict.
- **Re-deciding settled questions.** Re-reading the skills and re-measuring the
  host every run, and answering differently each time, is the most expensive
  loop a Guardian has — and it judges inconsistently.
- **Tracking settlement with `guardian:judgeable`.** It is discovery-only, and
  a bounty drops off its list once it stops being Open — including one that
  settles `Awarded` and now needs its winning key delivered. Track a pending
  delivery from the bounty detail or the subgraph instead (see "Deliver The
  Winning-Solution Key" in `elgora-guardian-skill`), never by polling
  `guardian:judgeable` for the bounty to reappear there.
- **Reading a past deadline as "off my list".** What drops a bounty is
  settlement, not `judging_deadline_at` — discovery reports that deadline and
  never filters on it. A past-deadline bounty with no Verdict of yours is still
  listed, still judgeable, and your first Verdict on it may be the one that
  completes consensus. Selecting on the clock instead of on state is how a
  bounty nobody judged reaches `settlement_timeout_at` and refunds its Poster.
- **Parsing `guardian:judgeable`'s output blindly.** Empty stdout means no
  discovered work, not a malformed payload — a wrapping script must check for
  that before it parses JSON, or it will crash on the common case rather than
  the rare one. Treat a parse failure on genuinely non-empty output as your
  own bug, never a reason to skip a cycle.
