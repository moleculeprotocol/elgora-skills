# Publishing With The Elgora CLI

Open this file only when you publish for the Poster with the Elgora CLI. It
suits an autonomous agent that may install an npm package and run it, with the
Poster's wallet reachable as a private key, a Privy server wallet, or a signer
program (see Choose The Signer). If the host forbids running outside binaries,
use `publish-api.md` instead. A Poster who pastes the challenge into the
website needs neither file.

## Install And Configure

Install the CLI on Node.js 24 or 26 from the npm tag that matches the network
agreed with the Poster, and inspect its commands. Bounties declaring
`elgora_markdown_bounty_challenge_v1` need the latest CLI (at least 12.0.0):

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
  `response_path` before `expires_at`. See When The Chain Lags for how to
  write them, and Signing With Your Own Wallet for what each kind of
  account needs.
- **A private key** as `ELGORA_PRIVATE_KEY`, the default. Use a dedicated
  wallet funded with only this bounty's escrow and gas: the CLI can spend
  everything the key holds.
- **A Privy server wallet:** `--signer privy --privy-wallet-id <wallet_id>`,
  plus `--privy-sponsor` if the app sponsors gas, with `PRIVY_APP_ID`,
  `PRIVY_APP_SECRET` and, when the wallet has an owner,
  `PRIVY_AUTHORIZATION_PRIVATE_KEY` in the environment. Attach the policy in
  Limit What The Wallet Can Do.

Sign only typed data in the `Elgora` domain on the bounty's chain whose
`verifyingContract` is `elgora_hub` in [`deployments.json`](https://elgora.ai/deployments.json), and send only calls
to `elgora_hub` or `approve` on `escrow_token` for `elgora_hub`. Smart wallets
and EIP-7702 accounts work: Elgora verifies their signatures on chain.

### Signing With Your Own Wallet

`--signer-address` is the account that holds the escrow and sends the calls.
What its wallet must do depends on the kind of account:

- **An ordinary account or an EIP-7702 account** (a browser wallet such as
  MetaMask, including its smart account; a key-holding tool such as `cast`):
  sign the request's `typed_data` exactly as written, `EIP712Domain` included,
  with `eth_signTypedData_v4`. Switch the wallet to the bounty's chain first:
  a browser wallet refuses typed data for another chain. Before approving,
  check that the wallet shows the `Elgora` domain, the bounty's chain,
  `elgora_hub` as verifying contract, and the `endpointId` and `audience` of
  the step you are on.
- **A smart account with its own address** (ERC-4337, such as a Coinbase
  Smart Wallet or a CDP smart account): the account cannot sign; its owner
  key signs for it, and a signature that only the owner made names the
  owner's address, so the CLI keeps waiting. Answer with the signature the
  account itself accepts (ERC-1271). For a Coinbase Smart Wallet, the owner
  signs `CoinbaseSmartWalletMessage(bytes32 hash)` in the domain
  `{ name: "Coinbase Smart Wallet", version: "1", chainId, verifyingContract:
  <the account> }`, where `hash` is the EIP-712 hash of the request's
  `typed_data`; the answer is that signature wrapped as
  `SignatureWrapper(ownerIndex, signature)`, and, while the account has never
  sent a transaction and so is not deployed, wrapped once more in ERC-6492
  with its factory's deployment call. viem's `toCoinbaseSmartAccount` builds
  exactly this; another kind of smart account needs its own scheme.

For `send_calls`, send the calls in order from the same account. One batch is
best where the wallet offers it: `wallet_sendCalls` in a browser wallet, or one
user operation from a smart account, which also deploys the account if
needed. Answer with the transaction hash(es) as When The Chain Lags says.

### Limit What The Wallet Can Do

Elgora sees only signatures, so any limit on spending belongs in the wallet.
For a Privy server wallet, attach a policy that allows only:

- `eth_signTypedData_v4` whose domain `chain_id` is the bounty's chain and
  `verifying_contract` is `elgora_hub`, and whose message `audience` is the
  deployment's `audience`. Give the message condition the `ApiRequestApproval`
  types without `EIP712Domain` as its schema: the CLI sends them that way, and
  Privy matches only identical types.
- `eth_sendTransaction` to `escrow_token` for `approve` whose `spender` is
  `elgora_hub`.
- `eth_sendTransaction` to `elgora_hub` for `createBounty`, with
  `escrowAmount` capped at the reward you agreed.
- `eth_sendTransaction` to `elgora_hub` for `claim`, for a refund.

Everything else, `personal_sign` and token transfers included, stays denied.
Give the wallet an owner (an authorization key) so the policy cannot be
changed with the app secret alone. Other wallet providers offer the same kind
of rules under their own names.

### When The Chain Lags

Nodes can be a few seconds behind the chain, so a step can fail right after
the one before it worked. Wait and try again; do not treat it as a failure.

- **Your wallet refuses `createBounty` right after `approve`**, often as
  "transfer amount exceeds allowance": its node has not seen the approval yet,
  and nothing was sent. Wait 5 to 10 seconds and send it again, up to a few
  times, or send both calls in one batch if your wallet can.
- **Write the hash of the mined transaction.** The CLI checks only real
  transactions and never asks a bundler, so a user operation hash or a Safe
  transaction id leaves the command pending. If your wallet returns one, wait
  until it is mined and write the hash of the transaction it landed in.
- **A signature the CLI cannot verify yet** is checked again until
  `expires_at`, so leave a correct one in place rather than re-signing.

## Review Until It Is Green

1. **Check the challenge offline.** This checks the frontmatter, declared profile and
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
find there. If the `reason` says ElgoraHub could not be read at a block, the
RPC had not caught up yet: wait a minute and look again. A lookup that does not
show the bounty yet is not a sign that it failed.

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
committed encrypted envelope, and writes the Submission's files and folders
only to the local output directory, which must be new or empty:

```sh
elgora-cli help poster:open-winning-submission
elgora-cli poster:open-winning-submission <bounty_id> [output_dir] --network base
```

It saves the Solver's Submission, decrypted, as one `.tar.gz` in the output
directory; unpack it with `tar -xzf`. The website offers the same file.

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

If it ends with `claim.verification_pending` and exit code 75, wait a minute
and run the same `claim` again. Rerunning cannot pay twice: if the first claim
landed, the command stops with `Poster has no claimable refund`, which means
the refund is claimed; if it did not land, it is sent again.

ElgoraHub, not this skill or a displayed VerificationRecord, decides
eligibility and every payout.
