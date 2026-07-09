# Paul off-stack ABAP Unit template

Reusable scaffold for the `@paul new-repo` routine (see
`wiki/agents/paul-dev.md` → "New-repo bootstrap"). Paul copies these files into a
target abapGit repo's `test-offstack/` folder and fills the per-repo judgement
fields. Canonical grounding for the shapes and the shim-vs-factory rule:
`[[abap-off-stack-transpiled-abap-unit-runner]]` and
`[[abap-off-stack-cut-isolation-shim-vs-factory]]` (cluster `abap-cloud`).

## Files

| Template file | Copy to (in target repo) | Repo-specific? |
|---|---|---|
| `run.mjs` | `test-offstack/run.mjs` | No — generic, dialect read from config |
| `package.json` | `test-offstack/package.json` | Only the `name` field |
| `package-lock.json` | `test-offstack/package-lock.json` | No — committed verbatim so `npm ci` is reproducible |
| `abap_transpile.json` | `test-offstack/abap_transpile.json` | **Yes** — `syntax_version`, `exclude_filter` |
| `README-offstack.md` | `test-offstack/README.md` | Fill the shimmed-adapter name |
| `gitignore-snippet` | append to repo `.gitignore` | No |
| `github-offstack-aunit-job.yml` | merge into an EXISTING `.github/workflows/abaplint.yml` | No |
| `abaplint.json` | repo root (GREENFIELD only) | Set `syntax.version.release` |
| `abaplint.yml` | `.github/workflows/abaplint.yml` (GREENFIELD only) | No |

## Static gate — greenfield vs existing repo

- **Repo already has abaplint CI** (an `abaplint.json` + a workflow): leave it. Confirm its dialect and merge
  only the off-stack job from `github-offstack-aunit-job.yml` beside the existing `lint` job.
- **Greenfield repo, no CI at all**: lay down the static gate from the template — `abaplint.json` at the repo
  root (set `syntax.version.release` to the target release, e.g. `v816`) and `abaplint.yml` at
  `.github/workflows/abaplint.yml` (it already carries both the `lint` and `offstack-aunit` jobs, so the
  off-stack job is not merged separately). `abaplint.json` is the tool's own `--default` output (185 rules,
  `abaplint/deps` dependency); do not hand-invent rules.

### Card-alignment tweaks applied to the raw `--default`

The template `abaplint.json` is the tool's `--default` with three deviations, all shaping the gate to the
dev-card (the card is the source of truth; abaplint is influenced by it, never the reverse):
1. `local_variable_names`, `method_parameter_names`, `class_attribute_names` set to `false`. The raw
   `--default` *requires* Hungarian `L_`/`I_`/`R_`/… prefixes on these, which directly contradicts
   `no_prefixes` (kept ON) and the card's user-confirmed no-prefix Precedence #1; the unedited default cannot
   pass on any real no-prefix code.
2. `method_length.statements` tightened `100` → `20`, matching card CA-METHODS-22. On a legacy-seeded repo,
   drop this one rule's severity to `Warning` rather than relaxing the number, to preserve the card's intent.
3. `local_class_naming.test` set to `^LTC_.+$` (from the `--default` `^LTCL_.+$`), matching the card's
   TDD-CONVENTIONS-07 test-class prefix `LTC_`. Consequence: local test classes must be named `LTC_*`, so a
   test named `LTCL_*` (ADT/abapGit muscle-memory) will be flagged; that is the card driving the gate, by
   design.

## The three per-repo judgement calls (no template can make these)

1. **Dialect** — set `syntax_version` in `abap_transpile.json` to match the repo-root
   `abaplint.json` (e.g. `v816`). If the repo has no `abaplint.json` yet, the routine
   adds one and asks the user which SAP_BASIS / release to target.
2. **Shim vs factory, and which class(es)** — for each collaborator a class-under-test
   defaults via `NEW <adapter>( )` that drags heavy DDIC, decide per the rule in
   `[[abap-off-stack-cut-isolation-shim-vs-factory]]`: factory-first only when the CUT
   has exactly one production call site; otherwise (including zero call sites) shim-first.
   Add each shimmed class to `exclude_filter` and drop an empty same-named `.clas.abap`
   (+ `.clas.xml`) into `shim/`.
3. **DDIC fixtures** — supply only the data elements / table types on the tested path as
   abapGit-serialised XML in `ddic/` (domain-less DTEL: `DD04V` with DATATYPE+LENG+OUTPUTLEN,
   no DOMNAME; TTYP: `DD40V` with ROWKIND=S, DATATYPE=STRU, ACCESSMODE=T, KEYDEF=D, KEYKIND=N).
   Do not transpile the adapter's heavy structures; `unknownTypes: "compileError"` makes a
   missing fixture fail loudly.

## Lockfile — commit it, do not regenerate per repo

`package-lock.json` ships in this template and is copied into `test-offstack/` verbatim; it is committed
alongside `package.json` so `npm ci` (used by both the local GREEN step and the CI job) is reproducible out
of the box. `npm ci` fails hard without a committed lockfile ("npm ci can only install with an existing
package-lock.json"), so there is deliberately no per-repo `npm install`-then-commit step. Regenerate the
template lockfile only when the pinned `devDependencies` in `package.json` change: run
`npm install --package-lock-only` in this folder (writes the lockfile without an on-disk `node_modules/`).

## Not this template's job

Serialising the ABAP package into the Git repo (that is abapGit inside the SAP
system, a human action) and pushing / merging (human owns push; Paul commits only,
never pushes).
