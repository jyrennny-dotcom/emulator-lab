# Friend link

## How it works

- The dashboard server listens on two ports, both on `127.0.0.1` only (not reachable from your network):
  - **8765**: your dashboard. Only this PC. Never shared.
  - **8766**: the friend side. Same dashboard, but every request needs the secret key.
- The dashboard server (`dashboard/lab/tunnel.py`) runs a Cloudflare quick tunnel pointing at port 8766 only, restarts it if it drops, and builds the link `https://<random>.trycloudflare.com/?key=<secret>`. Turn this off with `"autoShare": false` in `config/lab.json`.
- The **Updates** panel shows `data/updates.json`, so he can see what changed and what to test.
- When your friend opens the link, his browser stores the key as a cookie, so later clicks work.
- Both of you see the same live state and the same activity feed, refreshed every 2 seconds.

## What your friend can do

Everything on the dashboard except "Open window" (that window is on your PC). He uses the **Phone screen** button instead: click to tap, drag to swipe, mouse wheel to scroll, plus Back / Home / Apps keys and a text box for typing.

## Keep in mind

- Anyone who has the link can control the emulators and see whatever accounts are signed in on them. Send it only to him, in a private message.
- The link only works while the dashboard runs. Each restart gives a new web address.
- To make every old link stop working: `.\scripts\share-link.ps1 -NewKey`.
- The secret key lives in `data/friend-key.txt`. It unlocks only this dashboard, nothing else.
