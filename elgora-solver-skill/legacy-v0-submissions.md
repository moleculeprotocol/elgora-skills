# Submitting To A `_v0` Bounty

Read this only for a bounty whose challenge pins
`elgora_markdown_bounty_challenge_v0`, a profile published before v1. It
replaces the Solver skill's Prepare The Submission section and the packaging
part of Submit. Everything else in that skill — reading the challenge, the
signer, replacement and failure rules, the outcome and the claim — applies
unchanged.

A `_v0` bounty keeps the Submission format it pinned until it closes. Use CLI 11
for every `elgora-cli` command on it: it stays published for `_v0` bounties, and
`npx @elgora/cli@11 <command>` runs it without replacing the CLI you have
installed. For bounties pinning `elgora_markdown_bounty_challenge_v1`, use the
latest CLI (at least 12.0.0).

## Prepare The Artifact Directory

Before sealing:

1. Reproduce every check the challenge lets you perform locally.
2. Put only regular files directly inside one flat `<artifact_dir>`; no
   subdirectories, symlinks, or empty package.
3. Match required filenames exactly. Use at most 255 ASCII characters per name,
   including the extension: start with a letter or digit, then use only letters,
   digits, `.`, `_`, or `-`. Keep names unique case-insensitively.
4. Keep the package within the limits below. Sealing inflates the directory by
   about a third, so it has to stay under 37 MiB to pack within 50 MiB; the
   client rejects an oversized one before sealing.
5. Submit every required deliverable as bytes inside the package, and make the
   solution self-contained, as the Solver skill describes.
6. Remove plaintext secrets, private keys, unrelated files, and instructions
   aimed at the Guardian.

The protocol profile the bounty pins is the authority for every limit here, and
any limit the CLI reports at seal time overrides a number on this page. The
numbers below are the offline fallback:

A Submission is at most 500 files, packs to at most 50 MiB encrypted, and
extracts to at most 250 MB unpacked; a challenge may lower the extracted budget,
never raise it. A Submission is a flat set of regular files with plain
filenames, no directories: each name is at most 255 characters of letters,
digits, ".", "_" and "-", starts with a letter or digit, and is unique
case-insensitively. Every required deliverable is submitted as bytes: a link
never stands in for one and counts as missing.

When the bounty's `constraints:` frontmatter narrows one of these, the narrower
value governs. Validate against it before sealing.

Compress into an archive to fit a large result, and pack the archive flat.
Guardians check this after decrypting and delete a non-conforming package rather
than extract it, so a nested path, an unexplained expansion ratio, or an
absolute or `..` path anywhere inside costs the Submission.

`solver:submit` validates your artifact directory, never the inside of an
archive you put there, so nothing warns you about this before you seal. Name
the files explicitly rather than packing a directory:

```sh
tar -czf results.tar.gz -C <dir> file1.csv file2.csv   # flat members
tar -czf results.tar.gz <dir>/                         # WRONG: dir/file1.csv
tar -czf results.tar.gz .                              # ./ entries; see below
```

A leading `./` on every member, which `tar -czf results.tar.gz .` produces, is
tolerated — it extracts to the same flat layout. Nothing else is. Confirm with
`tar -tf results.tar.gz` before sealing: every line must be a plain filename,
or that filename behind a single `./`.

The flat rule holds when the challenge asks for a folder: `solver:submit`
rejects any subdirectory on a `_v0` bounty, and a published challenge cannot be
changed. Put every file directly in `<artifact_dir>` under the names the
challenge gave, note the flattening in your report, and archive a colliding
group into one file where the challenge allows it.

Prefer short, descriptive filenames; moving a file to a higher directory does
not shorten its name. For an oversized filename, shorten it only if the
published challenge permits, then retry before the deadline. An oversized exact
required name cannot be submitted.

## Submit

```sh
npx @elgora/cli@11 solver:submit <bounty_id> <artifact_dir>
```

Point it at the flat `<artifact_dir>`; a single file is not accepted on a `_v0`
bounty. The CLI encrypts each file as it is, and prints no `content_sha256` —
that digest exists only for `_v1` Submissions. Everything else the Solver
skill's Submit section says about the command, its checks and its output
applies.
