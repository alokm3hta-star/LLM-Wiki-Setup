# Off-stack ABAP Unit (`test-offstack/`)

This folder runs the repo's existing ABAP Unit tests **off-stack** — transpiled to
JavaScript and executed on Node, with **no live SAP system** — via the abaplint
transpiler and `open-abap-core`. It is a companion to the abaplint static gate,
not a replacement for on-stack verification.

## Run it locally

```bash
cd test-offstack
npm ci        # one-off: installs the transpiler + runtime
npm test      # transpiles the ABAP, then runs the tests on Node
echo $?       # 0 = all passed
```

`npm ci` installs strictly from the committed `package-lock.json`; run it once (or
after a dependency change), then `npm test` as often as you like.

## Run it in CI

The **same** `npm ci && npm test` runs automatically as the `offstack-aunit`
GitHub Actions job in `.github/workflows/abaplint.yml`, after the abaplint static
gate (`needs: lint`), on every push to `main` and every pull request. No SAP
system and no manual step; a red job blocks the PR. Watch a run with
`gh pr checks <PR> --watch`. Local and CI run the identical command, so a local
green is a faithful preview of the CI result.

## What is and is not verified off-stack

**Verified off-stack:** the orchestration / pure-ABAP logic — sequence,
commit-once, rollback, guard and duplicate branches, anything the transpiler
faithfully reproduces.

**NOT verified off-stack:** any class that calls classic BAPIs, the database, or
HTTP. Those collaborators are replaced by an empty **shim** so the transpile
resolves without dragging their DDIC in; the shim is never executed. The real
adapter class(es) — `REPLACE_WITH_SHIMMED_ADAPTER` — remain an **on-stack ATC +
ABAP Unit** concern.

An off-stack green is `[CI]` provenance only. In-system ABAP Unit and ATC remain
**UNVERIFIED pending a human abapGit pull + on-system run**. This gate never
claims otherwise; do not read "the tests run off-stack" as "the tests run
off-stack, full stop."

## Layout

- `run.mjs` — transpile runner (generic; dialect read from `abap_transpile.json`).
- `abap_transpile.json` — per-repo config: `syntax_version`, the shimmed-adapter
  `exclude_filter`, input folders.
- `shim/` — empty same-named fake(s) of the excluded adapter class(es).
- `ddic/` — minimal DDIC fixtures (data elements / table types) for the tested path.
- `package.json` — pins `@abaplint/transpiler` + `@abaplint/runtime` (same version)
  and `@abaplint/core`.
