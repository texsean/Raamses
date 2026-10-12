# RaamsesAgent — Progress Log

Running record of what is built, verified, and next. Newest first.
Kept in-repo so it survives sessions and is minable into the memory palace.

---

## 2026-09-12 — Phase 3 foundation: session_id is TEXT, not UUID

Branch `raamses/phase3-session-store`. Migration `0006` + repository/tests.

Found the first real Phase 3 blocker: the Phase 1/2 schema declared
`sessions.session_id UUID` and minted ids inside `sp_create_session` with
`gen_random_uuid()`. Hermes session ids are timestamp **strings**
(`20260912_113311_45eac8`) produced by the runtime and passed in by callers —
a UUID store can never hold a real session, so the port dead-ended on turn one.

`0006` rebuilds all 8 tables with `session_id TEXT` and rewrites
`sp_create_session` to **take the caller's id** (upsert), faithful to
`SessionDB.create_session(session_id, source, ...)`. All 11 stored functions
now take TEXT ids. The `sp_build_context` in 0006 is the budget-aware version
(0004 semantics — caught because re-creating the 0003 non-trimming body
clobbered the 0004 fix and 4 tests went red).

**Verified: 54 tests pass** against live Postgres.

Next (still Phase 3, same branch or a follow-up):
1. Full-fidelity columns — the stock SQLite `sessions` (~60 cols) and
   `messages` (~28 cols) are far wider than the v1 skeleton (7 / 12). The swap
   needs those columns (cwd, model_config, source, session_key, archived/pinned/
   hidden flags, started_at/ended_at, token accounting, ...) before the facade
   port. Additive `ALTER TABLE ... ADD COLUMN`, no re-drop.
2. Facade port — a `RaamsesSessionDB` overriding the ~15–20 hot-path public
   methods (create/get/end/list sessions, append_messages_batch,
   get_messages_as_conversation, get_meta/set_meta) over the repository,
   constructed when `storage.backend=raamses`. The ~195-method surface is NOT
   ported in one shot; non-hot-path methods (FTS search, portability, telegram
   topics, gateway, maintenance) stay on the stock path for now.

### Gotcha worth remembering

- Recreating a stored function from an OLDER migration silently reverts later
  migrations. 0006 re-declared `sp_build_context` from the 0003 body and wiped
  the 0004 budget fix; the token-budget tests are the tripwire. When a
  corrective migration re-declares a function, diff it against the LATEST
  definition, not the original.

---

## 2026-09-12 — Phase 1 verified, Phase 2 landed

### Phase 1 — Schema (DONE, verified)

Commit `befde78` — 8 tables, 6 stored functions, pgvector Postgres 16 compose.

Applied and confirmed live against the `raamses-postgres` container
(`pgvector/pgvector:pg16`, host port **55432**):

- Tables: `sessions` `messages` `tool_calls` `summaries` `memories` `skills`
  `turn_metrics` `file_sync`
- Functions: `sp_append_message` `sp_log_tool_call` `sp_upsert_memory`
  `sp_compact_session` `sp_recall` `sp_build_context`

Commit `bb7e1f7` — **`sp_build_context` budget fix** (migration `0004`).

The 0003 version returned every unsummarized message and left token trimming to
the caller. That violates charter criterion 2 ("already trimmed to budget") and
ships whole-session history over the wire every turn. 0004 walks sections in
priority order (`summary` > `memory` > `skill` > `message`), accumulates a
running token total, and stops emitting rows at the budget. Message rows are
emitted newest-first, so an over-budget session evicts its **oldest**
unsummarized turns — the correct order.

### Phase 2 — Repository layer (DONE, verified)

Commit `9184010` — `raamses/repository.py` behind the `storage.backend` flag.

- One method per stored function. No raw SQL above this module; a guard test
  greps the module source for `INSERT INTO` / `UPDATE sessions` / `DELETE FROM`
  / `CREATE TABLE` and fails if any leaks in.
- `_placeholders()` rejects unknown function names, so the call layer cannot be
  used to smuggle arbitrary SQL.
- psycopg3 pool, opened lazily on first use — importing the module on a machine
  with no Postgres is free, and stock Hermes is unaffected.
- Migration `0005` adds the session lifecycle functions Phase 1 missed:
  `sp_create_session` `sp_end_session` `sp_get_session` `sp_list_sessions`
  `sp_record_turn_metrics`. Without them the only path to a session row was a
  raw INSERT.

**Verified: 54 tests pass** (`22` stored-function + `32` repository) against
live Postgres. `backend_name()` correctly returns `hermes` with no config
present, so the stock path is untouched by default.

### Gotchas worth remembering

- **Pre-existing Windows test failures — not regressions.** `tests/hermes_state/`
  has 9 failures on this host that also fail on stock upstream `v0.21.1`
  (verified by running the same files in a clean worktree at `2237be3559`):
  5 in `test_shared_session_db_registry.py` and 4 in
  `test_state_db_file_identity.py`. All are POSIX inode-replacement semantics
  that Windows does not have (`PermissionError: [WinError 32]` — you cannot
  unlink a file another process holds open). Baseline for this repo on Windows
  is therefore **276 passed / 9 failed** in `tests/hermes_state`. Do not spend
  time "fixing" them and do not treat them as a Phase 3 regression signal;
  compare against this baseline instead.
- **psycopg sends untyped parameters as `unknown`**, which fails to resolve
  overloads against `VECTOR`/`JSONB`/`REAL` signatures — every stored-function
  call needs explicit per-argument casts (`%s::uuid`, `%s::vector(1536)`, ...).
  This cost one full round of test failures before the cast table existed.
- Migrations in `db/migrations/` are mounted at
  `/docker-entrypoint-initdb.d` and **only run against a freshly-initialized
  empty volume**. New migrations against a running instance must be piped in
  manually: `docker compose -f docker-compose.postgres.yml exec -T postgres
  psql -U raamses -d raamses -v ON_ERROR_STOP=1 < db/migrations/000N_x.sql`
- The repo has no local venv; Python deps land in the Hermes venv at
  `~/.hermes/hermes-agent/venv`. `psycopg[binary,pool]` and `pytest` were
  installed there.

### Config to enable the Postgres path

```yaml
storage:
  backend: raamses        # 'hermes' (default, stock SQLite) | 'raamses'
  dsn: postgresql://raamses:raamses_dev_password@localhost:55432/raamses
  pool_min_size: 1
  pool_max_size: 8
```

`RAAMSES_BACKEND` and `RAAMSES_DSN` override the config keys.

### Next — Phase 3

Port order per charter, one swap per branch + PR, tests green each time:

1. **session store** — the `SessionDB` facade (`hermes_state.py:327`) is the
   seam; its public methods ARE the session-store API, and all its SQL funnels
   through 5 executor functions (`hermes_state.py:773-886`, `:896-901`).
   Reimplementing the facade over the repository converts the whole domain at
   once, per Phase 0's finding.
2. **memory** — replace `MemoryStore` internals (`tools/memory_tool_store.py`).
   Watch the 3 out-of-band writers that bypass the store
   (`hermes_cli/web_routers/ops.py:467-486`, `agent/learning_mutations.py:59-63`,
   `hermes_cli/agent_import.py:361`) — they must be intercepted or memory
   diverges.
3. **skills** — full content port including sidecars.
4. **compaction** — `sp_compact_session` on the live path.

---

## 2026-09-07 — Phase 0 complete

4-agent read-only recon, `file:line` receipts for every state read/write.
Write-up: `docs/phase0-inventory.md`. Key finding: Hermes state is not mostly
markdown — it is one SQLite DB (`state.db`) plus scattered files, and
`SessionDB` is a single facade that makes the session port a facade swap rather
than a call-site-by-call-site rewrite.
