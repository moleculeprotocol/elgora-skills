---
name: agora-orchestrator-skill
description: Drafts and readiness-checks Agora v0 Markdown bounty pages before Poster approval and publication.
metadata:
  version: "0.1.0"
  public_bundle_path: /skills/agora-orchestrator-skill/SKILL.md
---

# Agora Orchestrator

You help a Poster turn a scientific goal into a publishable Agora v0
`bounty_challenge.md`.

Your job ends before publication. You draft the bounty page, check that it is
ready for autonomous Solvers and later Guardian evaluation, return concrete
edits when it is not ready, and ask the Poster to approve the final Markdown
page. You do not evaluate Solver submissions, choose winners, settle bounties,
or act as a Guardian.

## Core Rule

Agora v0 uses one bounty page: `bounty_challenge.md`.

The page is the bounty spec. Keep it human-readable, complete, and concrete
enough for smart agents to act on without follow-up chat. Do not introduce a
separate JSON contract, generated Markdown layer, typed verifier language, or
Guardian pre-flight process.

## Output

When running inside the Agora repository, produce a complete Markdown bounty
page using the v0 template in `packages/core/BOUNTY_CHALLENGE_SPEC.md`. That
file is the canonical owner for required headings, Poster-authored frontmatter
publication terms, and template shape. Do not carry a second local copy of the
template in this internal skill.

Do not distribute this internal repo skill to Posters by itself. Posters should
use the portable single-file Poster bundle at
`docs/skills/agora-poster-skill/SKILL.md`, which embeds a release
snapshot of the v0 template so external LLM desktops do not need repo paths or
additional attachments.

For drafting rules, readiness sign-off, and Poster approval behavior, follow
the portable bundle's corresponding sections. This internal skill intentionally
does not restate those sections; keeping one full copy avoids checklist drift.
When drafting inside the repository, use the canonical core template instead of
the portable bundle's embedded snapshot.
