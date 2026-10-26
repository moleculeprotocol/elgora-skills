# Judging A `_v0` Bounty

Read this only for a bounty whose challenge pins
`elgora_markdown_bounty_challenge_v0`, a profile published before v1. Run every
`elgora-cli` command for it with CLI 11: `npx @elgora/cli@11 <command>`. Every
other section of the Guardian skill applies.

A `_v0` Submission is a flat set of files, not an archive. `guardian:open`
writes each file under its own name into the output directory and overwrites
files already there, so give each Submission its own directory. It reports no
`content_sha256`.

Disqualify a `_v0` Submission that holds more than 500 files, a folder, a name
outside the filename rule (at most 255 characters of letters, digits, `.`, `_`
and `-`, starting with a letter or digit, unique ignoring case), or more than
250 MB, or a lower budget the challenge sets, once its archives are unpacked.
Archives inside it are handled as the Guardian skill describes.
