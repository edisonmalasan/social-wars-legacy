# Playing Social Wars Legacy

Social Wars was a Facebook game from 2012, and it is gone. This is a
preservation of it: the same rules, the same world, played in a browser
or on the desktop, with **no Flash anywhere** and **no account with
Zynga**.

## What you need

- A modern browser, or the desktop app.
- A server to play on — either the one that comes with the desktop app,
  or somebody else's.

The game is **not** on the web for you to sign up to. The server is
part of the project, and running one is the subject of
[`RUNBOOK.md`](RUNBOOK.md).

## Registering

Open the game and you are asked for a **name** and a **password**.

- The **name** is your player. It is what other players see, and it is
  what the server knows you by. It cannot be changed later.
- The **password** is yours. The server keeps a **salt and a hash** of
  it and never the password itself, so nobody — including whoever runs
  the server — can read it. If you lose it, you make a new account.

There is no email address, no Facebook, and no password reset. That is
deliberate: the original asked for a Facebook identity, and the
preservation does not.

## Playing

The game is the original's. You start with an empty town, a few
resources and a **tutorial** that walks you through the first things:
building, training a worker, collecting, putting up a factory, training
a soldier, and attacking.

- **Build** from the menu. The list is the original's, in the original's
  order, and the things you cannot afford yet are further down rather
  than hidden, so you can see what you are working towards.
- **Collect** when the timer is up. You choose how long to wait: five
  minutes gives you a quarter of a load, eight hours gives you three
  loads. You can hurry a neighbour up instead of waiting.
- **Train** units in your barracks and **place** them.
- **Attack** other players' towns. The fight is simulated by the
  **server**, so the result is the same for everyone and it cannot be
  faked.
- **Goals** are the spine of the game: the chapters on the map, the
  goals in them, and the rewards for finishing them.

## The interface

The game is scaled to fit your window rather than reflowed, because the
original's layout is not fluid and reflowing it would put the panels on
top of each other. On a phone the whole stage is scaled down, and the
text can get small — the game says so when it does.

## What is different from the original

- **No Facebook.** The original was a Facebook game: the photos, the
  invitations and the "assists" were all Facebook features. Here the
  neighbours are placeholders and there is no invitation system.
- **The art is not the original's.** Zynga owns it, so it cannot be
  shipped. The game's *behaviour* is preserved; the pictures are not,
  and they are being redrawn. See [`LICENSING.md`](LICENSING.md).
- **Some assets are missing.** Ten items have no art, and the 2012
  server's configuration is missing 73 assets. The game says which.
- **The servers are small.** This is a preservation, not a business:
  there is one server, a handful of players, and no queue.

## The rules are the original's

The rules were reimplemented from the **client**, which is the
specification: where the original's Python server and the client's
ActionScript disagreed, the client won, and every disagreement is
recorded. So:

- the daily bonus is a **five-day cycle**;
- the trade counter is **20 hours**, not a day;
- the collect timers are **5 minutes, 1 hour, 4 hours and 8 hours**;
- a battle is decided by a **server-issued seed**, so the same fight
  always goes the same way and nobody can claim a result.

## If something is wrong

The server's own dashboard is at **`/dashboard`**, and it says which
versions are running and what is unhappy. If the game will not start,
the most likely reasons are:

- the server is not running — `/health` should answer `{"status":"ok"}`;
- your session has **expired** — it lasts 30 days, and signing in again
  fixes it;
- the window is too small for the text to be readable — the game says
  so.

The server's owner will know more; see [`RUNBOOK.md`](RUNBOOK.md).
