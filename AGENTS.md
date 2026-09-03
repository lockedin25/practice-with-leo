# Night Shift — Agent Society Charter

This repository is operated autonomously overnight by a small society of agents
(claude, codex, opencode), each working in its own git worktree on branch
`agent/<name>`. A coordinator (foreman) composes tasks, merges branches, and
relays handoffs.

## Rules for any agent working in this repo
1. Work only in your own checkout. Never touch other agents' worktrees.
2. Commit on your current branch only. Never push, never rebase shared branches.
3. Read `_society/INBOX.md` if present — it is authoritative context.
4. Write your handoff to `_society/OUTBOX.md` exactly per the protocol in your task.
5. Keep changes focused on the task spec. No scope creep.

## Wiki reflection opt-out
Per the global convention, this project OPTS OUT of Personal Wiki reflection.
All artifacts stay inside this repository. Not updating the wiki here is
correct behaviour, not a miss.
