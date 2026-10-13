# Publishing With The Elgora CLI

Open this file only when you publish for the Poster with the Elgora CLI. It
suits an autonomous agent that may install an npm package, run it, and hold the
Poster's private key in its host's secret store. If the host forbids running
outside binaries, or the wallet signs for you without handing over a key, use
`publish-api.md` instead; the CLI signs only with a local key. A Poster who
pastes the page into the website needs neither file.

## Install And Configure

Install the CLI on Node.js 24 or 26 from the npm tag that matches the network
agreed with the Poster, and inspect its commands. On Node 26 the CLI must be
10.2.0 or newer:

```sh
npm install --global @elgora/cli@latest   # mainnet
npm install --global @elgora/cli@next     # testnet
elgora-cli help poster:review
elgora-cli help poster:publish-fund
```

`latest` is the release that matches what runs on mainnet; `next` is the
release being rolled out on the testnet first. A tag selects a version, not a
network: still pass `--network` as below. If either `help` command reports an
unknown command, the installed CLI is older than this skill: install again
from the tag.

Both deployments in `SKILL.md`'s Mainnet Or Testnet table are built into the
CLI, which selects one per command: `--network base` for mainnet, the default,
or `--network base-sepolia` for the testnet. It prints a notice on stderr when it
fell back to the default. Pass the network agreed with the Poster on every
command, and keep it for every step of the bounty.

The examples below use `--network base`. On the testnet, write
`--network base-sepolia` in every command instead. Never set
`ELGORA_HUB_ADDRESS`, `ELGORA_ESCROW_TOKEN_ADDRESS`, `ELGORA_RPC_URL` or
`ELGORA_API_BASE_URL` for one of these two deployments: the CLI already holds
a matching set, and one value from the other deployment breaks it.

Keep `ELGORA_POSTER_PRIVATE_KEY` in the host's secret manager and expose it
only to the command process. Never put it in the challenge, prompt, shell
history, logs or source control. If no process-local secret injection is
available, use `publish-api.md` with a wallet that signs for you, or hand the
page to the website.

## Review Until It Is Green

1. **Check the page offline.** This checks the frontmatter, pinned profile and
   declared limits without a model, network request or review quota. Fix its
   reported issues before going on.

   ```sh
   elgora-cli check-page bounty_challenge.md
   ```

2. **Review the exact draft.** Record this draft's commitment before each
   attempt, including attempts that are rejected:

   ```sh
   elgora-cli spec-commitment bounty_challenge.md
   elgora-cli poster:review bounty_challenge.md --network base
   ```

   `review.ready` returns the commitment and `approved_until`, and may list
   `warnings` that never block publication. `review.not_ready` prints every
   issue, with `code`, `anchor` and `hazard`, and exits 2. One issue may stand
   for several wordings of the same problem: `other_wordings` keeps the
   others. Any other failure exits 1 and is not an approval.

3. **Revise and resubmit** as `SKILL.md` describes, naming the draft you just
   sent:

   ```sh
   elgora-cli poster:review bounty_challenge.md --network base --previous <previous_spec_commitment>
   ```

   New reviews use the signing wallet's rolling 24-hour quota; identical bytes
   already approved on the same deployment are not charged again. The CLI
   signs a fresh request on every attempt. For a `429`, wait until the
   indicated retry time. Report service failures rather than retrying in a loop
   or changing the page to work around them.

## Publish And Fund

Straight after `review.ready`, publish the unchanged file on the same network:

```sh
elgora-cli poster:publish-fund bounty_challenge.md --network base
```

The command publishes the exact bytes, checks the returned commitment, chain,
ElgoraHub and escrow token against its own values, and only then funds. It
needs enough USDC for the reward and some ETH for gas on that chain, and
refuses to start without them. Where the wallet supports it, it funds in one
transaction with a USDC authorization; otherwise it sends `approve`, then
`createBounty`. It prints one JSON line per step; the last,
`publish_fund.bounty_created`, carries `bounty_id`, `spec_commitment` and
`tx_hash`. Keep all three. They are public.

If publication returns `bounty_challenge_not_ready`, nothing was published:
the bytes had no ready approval from the last seven days on that deployment,
so publication reviewed them and they failed. Return to the review loop.

Mainnet funding escrows real USDC. A published page whose funding transaction
never lands is harmless: running the command again on the same file yields the
same `spec_commitment` and tries again. After publication, any material change
requires a new bounty and a new `spec_commitment`.

Creation pins the configured Guardian roster to the bounty and funds
winner-take-all escrow. Publishing a challenge never authorizes a later
Verdict, claim, refund, or delivery action.

## Follow The Final Result

ElgoraHub finalizes as one of:

- `Awarded`: the winning Solver can claim the reserved winner-take-all award
  directly. The funding Poster can retrieve and decrypt the winning Submission
  locally with the same funding wallet once a roster Guardian has delivered
  its key after settlement.
- `NoValidSubmission`: the Poster can claim the queued refund.
- `TimedOut`: the Poster can claim the full escrow refund.

For an Awarded bounty, retrieve the exact finalized winner. The command creates
a one-time key, signs both requests with the funding Poster's key, verifies the
committed encrypted envelope, and writes plaintext only to the local output
directory:

```sh
elgora-cli help poster:open-winning-submission
elgora-cli poster:open-winning-submission <bounty_id> [output_dir] --network base
```

If the winner cannot be opened yet, the error says why in its `next_action`;
follow it.

For a refund, inspect the claim command before using it:

```sh
elgora-cli help claim
elgora-cli claim --claimant-address <wallet_address> <bounty_id> --network base
```

With `--claimant-address` the command prints prepared calldata for that wallet
to sign. Without it, it signs locally and requires `ELGORA_CLAIMANT_PRIVATE_KEY`.
ElgoraHub, not this skill or a displayed VerificationRecord, decides
eligibility and every payout.
