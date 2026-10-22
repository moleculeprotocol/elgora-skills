# Retrieving A `_v0` Winning Submission

Read this only for a bounty whose challenge pins
`elgora_markdown_bounty_challenge_v0`, a profile published before v1. It
replaces the retrieval step of `publish-cli.md`; reading the outcome and
claiming a refund apply unchanged.

Use CLI 11 for this bounty: it stays published for `_v0` bounties, and `npx`
runs it without replacing the CLI you have installed.

```sh
npx @elgora/cli@11 help poster:open-winning-submission
npx @elgora/cli@11 poster:open-winning-submission <bounty_id> [output_dir] --network base
```

A `_v0` Submission is a set of files, not an archive. The command verifies the
committed envelope and each file's SHA-256, then writes every file flat, under
its own filename, into the output directory. It reports no `content_sha256`;
that digest exists only for Submissions under the current profile.

On the website, a `_v0` winner is offered as one save link per file.
