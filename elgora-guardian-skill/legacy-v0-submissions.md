# Judging A `_v0` Bounty

Read this only for a bounty whose challenge pins
`elgora_markdown_bounty_challenge_v0`, a profile published before v1. Its
Submissions keep the format that profile fixed. This file replaces the Guardian
skill's description of what `guardian:open` writes and its What
guardian:open Checks section; everything else in that skill — opening
the exact pair, the three outcomes, checking the page, judging, failures,
recording the Verdict and delivering the key — applies unchanged.

Use CLI 11 for every `elgora-cli` command on this bounty: it stays published
for `_v0` bounties, and `npx @elgora/cli@11 <command>` runs it without replacing
the CLI you have installed. For bounties pinning
`elgora_markdown_bounty_challenge_v1`, use the latest CLI (at least 12.0.0).

## What `guardian:open` Writes

A `_v0` Submission is a set of files, not an archive. `guardian:open` writes
each file flat, under its own filename, into the output directory you name,
which must be new or empty. It reports no `content_sha256`; that digest exists
only for current Submissions.

Besides the cases the Guardian skill lists, category 1 covers a `_v0` filename
outside the profile's filename rule and more files than the profile allows.

## Vet What The Package Actually Contains

Storage checks only the packed size; everything else is unverifiable until you
decrypt, so vet each Submission after opening and before extracting anything.

A Submission is at most 500 files, packs to at most 50 MiB encrypted, and
extracts to at most 250 MB unpacked; a challenge may lower the extracted budget,
never raise it. A Submission is a flat set of regular files with plain
filenames, no directories: each name is at most 255 characters of letters,
digits, ".", "_" and "-", starts with a letter or digit, and is unique
case-insensitively. The flat rule holds inside every archive the package
carries. Every required deliverable is submitted as bytes: a link (URL, DOI,
CID, bucket path, repository reference) never stands in for one and counts as
missing, though citing a source beside its bytes is fine.

`guardian:open` reports the current extracted ceiling as `max_extracted_bytes`;
prefer that number over this page.

**Inspect before you extract**, with commands that read only the index:

```sh
stat -c '%s %n' guardian-open/<bounty_id>/<submission_commitment>/*
file <artifact>                 # what it is, not what it is named
unzip -l <artifact>.zip         # or: zipinfo -t <artifact>.zip
tar -tvf <artifact>.tar.gz      # listing only; no -x
7z l <artifact>.7z
```

Run these inside the sandbox, on the decrypted package, not on the host. A
lister that is missing is installed into the sandbox from a public source — it
is ordinary tooling, and no bounty is refused over it.

Total the declared uncompressed sizes, add the unarchived files beside them, and
decide before anything reaches disk. **Disqualify that one Submission** —
category 1, recorded against that Solver and no one else — when it:

- is not flat: after stripping one leading `./` from each member name, a name
  still holds a path separator, or the listing carries a directory entry other
  than `./` itself;
- extracts past the ceiling, or past a lower budget the challenge sets;
- expands at a ratio with no legitimate explanation for its data;
- nests archives past the depth the challenge needs, or has a listing that
  disagrees with what extracts;
- carries entries with absolute paths, `..` traversal, symlinks or device files.

Every one of those is computed from the package's own form, so every honest
Guardian reaches the same answer from the same bytes.

The `./` carve-out is deliberate. `tar czf pkg.tar.gz .` — the most natural way
to pack a directory — writes a `./` entry and prefixes every member with `./`,
yet extracts to exactly the flat layout the rule protects, and no client-side
check sees inside an archive to warn the Solver first. Nothing else relaxes:
`results/`, `a/b.csv`, `../x`, an absolute path, a symlink or a device file
each disqualify as before, and a leading `./` never excuses what follows it.

A link offered where the challenge requires a deliverable is **not** one of
them: the package is valid, the deliverable is missing, and it fails the
acceptance criteria — category 2, as the Guardian skill explains.

Do not extract one you have rejected, and delete whatever was written for it.
Never repair one: no flattening a tree, renaming collisions, or extracting only
the parts you wanted. Record the reason in the Verdict body and judge the rest.
Each is that one Solver's failure, never an open failure on the bounty.

A Submission within the ceilings is legal, so a runner that cannot afford it is
an operational failure, never that Solver's. Bound disk, memory and wall time
before extracting; never raise a bound mid-run.
