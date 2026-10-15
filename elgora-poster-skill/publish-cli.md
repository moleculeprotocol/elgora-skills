# Publishing With The Elgora CLI

Open this file only when you publish for the Poster with the Elgora CLI. It
suits an autonomous agent that may install an npm package and run it, with the
Poster's wallet reachable as a private key, a Privy server wallet, or a signer
program (see Choose The Signer). If the host forbids running outside binaries,
use `publish-api.md` instead. A Poster who pastes the challenge into the
website needs neither file.

## Install And Configure

Install the CLI on Node.js 24 or 26 from the npm tag that matches the network
agreed with the Poster, and inspect its commands. This file needs CLI 11.0.0
or newer:

```sh
npm install --global @elgora/cli@latest   # mainnet
npm install --global @elgora/cli@next     # testnet
elgora-cli help poster:review
elgora-cli help poster:publish-fund
elgora-cli help check-challenge
```

`latest` is the release that matches what runs on mainnet; `next` is the
release being rolled out on the testnet first. A tag selects a version, not a
network: still pass `--network` as below. If any `help` command reports an
unknown command, the installed CLI is older than this skill: install again
from the tag.

Both deployments in `SKILL.md`'s Mainnet Or Testnet table are built into the
CLI, which selects one per command: `--network base` for mainnet, the default,
or `--network base-sepolia` for the testnet. It prints a notice on stderr when it
fell back to the default. Pass the network agreed with the Poster on every
command, and keep it for every step of the bounty.

The examples below use `--network base`. On the testnet, write
`--network base-sepolia` in every command instead. Never pass `--hub-address`,
`--rpc-url` or `--api-base-url`, or set their `ELGORA_` variables, for one of
these two deployments: the CLI already holds a matching set, and one value from
the other deployment breaks it.

## Choose The Signer

Pass the same signer options to every command of the bounty, and keep every
secret in the host's secret manager, exposed only to the command process.

- **Your own wallet tooling**, so no key enters the CLI process:
  `--signer manual --signer-address <address>`. Run the command in the
  background and read its stdout. For each signature or transaction it prints
  `signer.request_written` with `request_path`, `response_path` and
  `expires_at`. The request holds `kind`, `address`, `chain_id`, and
  `typed_data` (EIP-712, `eth_signTypedData_v4` shape), `message` (hex for
  `personal_sign`) or `calls`. Sign or send it with your wallet and write the
  signature, or the transaction hashes separated by spaces, to
  `response_path` before `expires_at`.
- **A private key** as `ELGORA_PRIVATE_KEY`, the default.
- **A Privy server wallet:** `--signer privy --privy-wallet-id <wallet_id>`,
  plus `--privy-sponsor` if the app sponsors gas, with `PRIVY_APP_ID`,
  `PRIVY_APP_SECRET` and, when the wallet has an owner,
  `PRIVY_AUTHORIZATION_PRIVATE_KEY` in the environment.

Sign only typed data in the `Elgora` domain on the bounty's chain whose
`verifyingContract` is `elgora_hub` in `deployments.json`, and send only calls
to `elgora_hub` or `approve` on `escrow_token` for `elgora_hub`. Smart wallets
and EIP-7702 accounts work: Elgora verifies their signatures on chain.

## Review Until It Is Green

1. **Check the challenge offline.** This checks the frontmatter, pinned profile and
   declared limits without a model, network request or review quota. Fix its
   reported issues before going on.

   ```sh
   elgora-cli check-challenge bounty_challenge.md
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
   or changing the challenge to work around them.

## Publish And Fund

Straight after `review.ready`, publish the unchanged file on the same network:

```sh
elgora-cli poster:publish-fund bounty_challenge.md --network base
```

The command publishes the exact bytes, checks the returned commitment, chain,
ElgoraHub and escrow token against its own values, and only then funds. It
needs enough USDC for the reward and refuses to start without it; the wallet
pays gas unless its provider sponsors it. With a private key on an ordinary
account it funds in one transaction with a USDC authorization; every other
signer sends `approve` for exactly the escrow amount, then `createBounty`. It
prints one JSON line per step; the last, `publish_fund.bounty_created`, carries
`bounty_id`, `spec_commitment` and `tx_hash`. Keep all three. They are public.

If the command instead ends with `publish_fund.verification_pending` and exit
code 75, the funding may already be on chain but is not confirmed. **Do not run
it again:** a rerun funds a second bounty. Look up the `tx_hashes` it printed,
or the Poster's bounties on ElgoraHub, and continue with the `bounty_id` you
find there.

With `--prepare-only` the command publishes but sends nothing: it prints
`publish_fund.calls_prepared` with the `approve` and `createBounty` calls for
the wallet to send itself, in order, from the Poster's address. Then read the
bounty id from that `BountyCreated` event.

If publication returns `bounty_challenge_not_ready`, nothing was published:
the bytes had no ready approval from the last seven days on that deployment,
so publication reviewed them and they failed. Return to the review loop.

Mainnet funding escrows real USDC. A published challenge whose funding transaction
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
elgora-cli claim <bounty_id> --network base
```

It sends the claim from the Poster's signer, with the same options as above.
With `--prepare-only`, it prints `claim.calls_prepared` for the Poster's wallet
to send instead.
ElgoraHub, not this skill or a displayed VerificationRecord, decides
eligibility and every payout.
