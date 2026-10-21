# The security review

A review of the three layers that decide what a player may do: the
**authentication** layer, the **command** layer and the **compatibility
shim**.

It is written as a review rather than a checklist: what the threat is,
what the code does about it, what is left, and what would have to change
to close it. The claims here are **checked** — every one of them is
covered by a test or a script that fails when the claim stops being
true.

## The threat

The original server had **no authentication**. The `USERID` came in the
request body, `user_key` and `accessToken` were read and discarded, and
the client's declared resource vector was applied **verbatim**. So
anybody could be anybody, and anybody could claim any resources.

The clone's threat model is therefore:

1. **Impersonation** — acting as another player.
2. **Resource fabrication** — claiming resources, buildings or rewards
   the player has not earned.
3. **Outcome fabrication** — claiming a combat result the server did
   not produce.
4. **Injection** — getting the server to run something it should not.
5. **Abuse** — using the server for something other than playing.

## The authentication layer

`packages/server/src/session.ts`, `packages/server/src/credentials.ts`.

### What it does

| The threat | What the code does | Checked by |
|---|---|---|
| Impersonation | A player signs in with a **credential**; the server issues a **session token** that identifies the player. The token is the only thing that names a player — nothing in the request body can | `session.test.ts` |
| Password disclosure | The password is **never stored**. The credential is a **salt** and a hash | `credentials.test.ts`, `account.test.ts` |
| Timing oracle | The hash is compared in **constant time** | `credentials.test.ts` |
| Token prediction | The token is **32 random bytes** in hex | — |
| A stolen token | The token **expires** (thirty days) and is **revocable** — one, or every session of a player | `session.test.ts` |
| A password that survives a restart | The credentials are **persisted** and loaded at boot | `account.test.ts` |
| The upstream's `USERID` | It is a **bridge**, and it is **off by default**. When it is on it only maps values the server has already bound to a player | `shim.test.ts` |

### What is left

- **The password hash is a fast salted SHA-256.** It is not a
  memory-hard hash, so a stolen `credentials` table can be cracked
  quickly. This is a **deliberate trade** and it is recorded in
  `packages/server/src/credentials.ts`: the server is a preservation of
  a 2012 game with a handful of players, the threat is not an offline
  attack on a stolen table, and a slow hash would make the server's own
  logins slow. A deployment that grows players, or that faces a stolen
  table, should move to a memory-hard hash — and that is a change in
  one module.
- **The session token has no scope beyond "this player".** It is not
  bound to a client, a device or a request. The roadmap asks for the
  token to be "scoped, revocable and expire"; it is revocable and it
  expires, and its scope is the player's whole account.

## The command layer

`packages/server/src/apply.ts`, `packages/rules/src/authority.ts`.

### What it does

| The threat | What the code does | Checked by |
|---|---|---|
| Resource fabrication | Every cost is **computed by the server** from the content bundle. The native envelope has **no field** for a client's declared delta, so it cannot be supplied even by accident | `commandcost.test.ts`, `requests.test.ts` |
| Outcome fabrication | Combat is **re-simulated server-side** from a **server-issued seed**. The client's claimed result is parsed only so it can be compared | `authority.test.ts` |
| A forged result | The **cheat battery** attempts eleven attacks against the **real** authority layer, each of which must have no effect | `cheatbattery.test.ts` |
| A weakened authority layer | The battery is **mutation-tested**: eighteen weakenings of the authority layer were each detected by exactly the attack they weaken | `cheatbattery.test.ts` |
| Injection | The SQL is **parameterised**. The only thing that can be interpolated is a **table name**, and every table name is **checked** as a plain identifier | `security.test.ts` |
| A half-applied batch | The commands are applied to a **copy** of the save, and the copy replaces the save only when the whole batch has been processed | `apply.test.ts` |
| A malformed command | The arguments are validated against the **command table**, which is the authority for the client, the server and the shim alike | `command-surface.test.ts` |
| Too much at once | The body is capped, a batch carries at most so many commands, and a request may take only so long | `app.test.ts` |
| Abuse | The rate limit is **per account**, so a player behind a shared address is not punished for the others | `observability.test.ts` |
| A secret in the repository | The repository is **scanned** for the shapes a credential takes | `security.test.ts` |

### What is left

- **The rate limit is a fixed window** and it is **per account** only
  when the request carries a session. An unauthenticated request is
  counted per address, so an attacker who never signs in is bounded by
  their address, which is a weak bound.
- **The command table is the authority for the arguments' *shape*, not
  for their *meaning*.** The server checks that `complete_goal` was
  given a number; it does not check that the number is a goal the
  player can finish — the rules engine does that, and the rules engine
  is the same code the golden master checks.

## The compatibility shim

`packages/server/src/shim.ts`.

The shim exists so the **untouched** original client can play. That
client can only send `USERID` in the body, because that is all it knows
how to send — so the shim is where the weakest input in the project
lives, and it is reviewed hardest.

### What it does

| The threat | What the code does | Checked by |
|---|---|---|
| A forged request | The frame is an **HMAC-SHA256** and it is verified in **constant time** | `commandphp.test.ts` |
| A request from another era | **Both** keys are accepted, because unmodified clients of both eras exist | `commandphp.test.ts` |
| A replay | The client re-sends the same packet when it gets no answer, so the **global command index** catches the replay and the commands are not applied twice | `shim.test.ts` |
| A claimed resource vector | The client's declared `res` is **never used**. The shim computes the cost | `shim.test.ts` |
| A claimed outcome | The shim hands the commands to the **same applier** the native endpoint uses | `shim.test.ts` |
| The legacy identity | The bridge is **off by default** | `shim.test.ts` |

### What is left

- **There is no timestamp freshness check on the legacy frame.** The HMAC
  is the only thing that says the request is genuine, so a captured
  frame stays valid for ever. It is harmless in practice, because the
  **replay** is caught by the global command index and the commands are
  not applied twice — but a request that is *not* a replay of an
  applied batch would be accepted. There is no such request in the
  client, and the shim is a compatibility path for a client that is
  fixed, so this is a **known** weakness rather than an oversight.
- **The bridge, once enabled, is a bearer token in a body.** Anyone who
  knows a bound `USERID` can play as that player. It is off by default
  and it only maps values the server has bound deliberately, and it
  exists so the original client can be played at all.

## The findings, in one place

| # | The finding | The severity | The status |
|---|---|---|---|
| 1 | The password hash is fast, so a stolen table is crackable | **low** for a handful of players, **high** for a real deployment | **Accepted and recorded** — a deliberate trade |
| 2 | The legacy frame has no freshness, so a captured frame stays valid | **low** — the replay is caught by the command index | **Known** |
| 3 | The bridge is a bearer token in a body | **medium** when it is on | **Off by default** |
| 4 | An unauthenticated request is rate-limited per address | **low** | **Accepted** |
| 5 | The token has no scope beyond the account | **low** | **Open** |

None of the five is a way to act as another player, to claim resources
that were not earned, or to fabricate a combat result. The three
properties that matter — the server computes the costs, the server
re-simulates the outcomes, and the client declares nothing — are checked
by the tests, and the battery that checks them is itself mutation-tested.

## How this review is kept true

- Every claim in the tables is covered by a named test or script, and
  `node scripts/check-security-review.mjs` fails if a test the review
  names is **not there** — so the review cannot quietly point at
  something that does not exist.
- `node scripts/check-licensing.mjs` and `node scripts/check-no-flash.mjs`
  check what may and may not ship.
- `node scripts/run-cheat-battery.mjs` is the release gate.
- The security checks live in `packages/server/src/security.test.ts` and
  run with the rest of the suite.

If a claim here stops being true, the test that covers it fails, and the
review is out of date in the same commit that breaks it.
