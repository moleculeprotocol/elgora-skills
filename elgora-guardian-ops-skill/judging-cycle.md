---
metadata:
  version: "1.2.0"
  updated: "2026-10-26"
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
- while a run works it, which run holds it and since when;
- each long job in flight: its container name, what it covers, and where its
  results land.

Keep it short: state, not narrative. Every run re-reads it, so progress prose
belongs in your report. Write a result into it the moment the result lands, not
on a later run.

**Every session claims the hold first, scheduled or interactive.** Before
writing to a bounty's directory, read the hold; if another session holds it
and the hold is younger than your runtime's maximum run time, leave the bounty
alone — an operator's word that nothing else is running does not replace this.

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
   hash still matches what is on disk; otherwise redo that step alone. Use the
   bytes a stored step verified rather than deriving them again: re-extracting
   text through a JSON tool can change a byte.
5. A job the record names is still running: collect any results that landed,
   say "in progress" in one line, and end the run. Do not re-verify finished
   work, re-read logs or re-list processes to say the same thing.
6. Out of budget before every Submission is resolved: stop cleanly, write the
   record, record no Verdict. That is normal for a large bounty — not a failure,
   and never a reason to score from incomplete evidence.
7. Every Submission resolved: decide, record the Verdict, confirm it on chain.
   Exit `75` with `guardian_verdict.verification_pending` means it may be on
   chain but is not confirmed yet: keep the record, keep the decision, and
   run the same `guardian:verdict` command on the next cycle. An identical
   Verdict already on chain is a no-op, so the retry never records twice.
   After an `awarded` Verdict, schedule the key-delivery follow-up before the
   run ends.
8. Delete every decrypted file for that bounty. Keep the record only while an
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
- **Probe, then plan.** Before the first full run, time and size the most
  expensive step once on the largest input (see "Sizing And Long Runs" in the
  operations skill), multiply it out against the time left before
  `judging_deadline_at`, and write the plan into the record.
- **Map every Submission at vetting, in one pass.** Read each one's run
  instructions and output format before writing the harness that drives them
  and the parser that reads them, and normalise results into one shape as they
  land. A harness that meets a new interface mid-run fails mid-run.
- **Settle what you can early.** Run each Submission's cheapest deciding check
  first and stop it once its result is settled, as the judging skill allows.
  Start the likely winner's longest runs early, since it is the one whose every
  criterion must be confirmed.
- **Build the reference once per bounty**, from the challenge's fixed inputs,
  and compare every Submission to it. A Submission that reproduces it has met
  that criterion; save deep review for one that disagrees or that static
  inspection flagged.
- **Split narrowly.** One worker per Submission, given the challenge, the
  reference and its own Submission — nothing about the others — at most two at a
  time, and never two compared measurements at once. Workers return findings
  into the record; you decide, and only you touch keys and transactions.
- **Report per run:** bounties advanced and to which stage, Verdicts recorded,
  spend per bounty.

## Pitfalls that cost real Guardians

- **Waiting by polling.** A run that sleeps and checks, or a schedule that wakes
  the agent only to report "still running", resends the whole context each
  time to learn nothing. Wait on the job (`docker wait`, notify-on-complete), or end
  the run and let the next scheduled one collect the result.
- **Fixing your harness under a running job.** A job that loaded the old script
  keeps writing results with the old bug. Stop it and rerun, or mark everything
  it produces untrusted and replace it; never patch over it.
- **Hand-copied identifiers.** Image digests, transaction hashes and
  commitments are read from their source (`docker images`, JSON output, the
  chain), never retyped.
- **Resuming a failed unit as done.** A resumable job skips only units that
  succeeded; one that recorded a failure is retried.
- **Stale scratch space.** Decrypted files from an abandoned attempt pile up.
  Check disk headroom before a reproduction and remove scratch for bounties
  that are resolved or no longer discovered.
- **Out of budget is not a failed Submission.** An unfinished evaluation is
  deferred, never judged.
- **Shifting order.** Re-deriving the order from array position reshuffles what
  looks done. Anchor it to `submission_call_count`.
- **Partial Verdicts.** There are none. Progress lives in the record and your
  operator reports, never on chain.
- **Re-deciding settled questions.** Re-reading the skills and re-measuring the
  host every run, and answering differently each time, is the most expensive
  loop a Guardian has — and it judges inconsistently.
