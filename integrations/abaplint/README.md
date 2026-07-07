# abaplint shift-left quality gate

An abaplint quality gate for an abapGit-serialised ABAP repository, run on the pull request, with no SAP system required. This accompanies blog Part 6 (the abaplint shift-left follow-up).

> **These are sanitised templates, not a universal drop-in.** The two files shipped here, `abaplint.json` and `abaplint.yml`, are a worked starting point. They encode one reasonable set of choices for a classic on-stack S/4HANA backend. Read them, then adapt the handful of fields called out under "Adapting the config" to your own release, namespace, and naming convention before you rely on the gate.

## What it is and how it works

abaplint is a static analysis and linting tool for ABAP that reads abapGit-serialised source directly from your Git repository. It never connects to an SAP system; it parses the `src/**` XML and ABAP files in the pull request itself.

The workflow here runs abaplint inside GitHub Actions on every pull request. It analyses everything under `src/**`, then annotates its findings inline on the changed lines, so a reviewer sees the issues in the PR without leaving GitHub. Because it runs entirely on the GitHub runner against serialised source, it needs no backend connection, no RFC, and no ATC run.

Treat this as additive to the ABAP Test Cockpit (ATC), not a replacement. abaplint catches a number of Clean ABAP patterns and craft issues that ATC covers only partly or not at all, and it does so before the change ever reaches the system. ATC on the backend remains the authority for system-context checks and for the formatting rules deliberately left out of this config. The two are complementary: abaplint shifts a first pass left onto the PR; ATC stays as the in-system gate.

## Licensing and cost

This is the question readers ask most, so it is worth stating precisely.

abaplint itself, both the CLI (`@abaplint/cli`) and the GitHub Action (`abaplint/actions-abaplint`), is MIT-licensed. This folder ships only your own two files, `abaplint.json` and the workflow, and contains none of abaplint's code. The workflow merely references the Action with `uses: abaplint/actions-abaplint@main`, which GitHub fetches at run time, and `npx @abaplint/cli`, which npm fetches at run time. Nothing is vendored or bundled here. MIT's "retain the notice" clause only triggers when you copy the licensed code, which this folder does not do, so no third-party licence obligation attaches to it; it ships under the kit's own MIT LICENSE.

Cost is where the two ways of running abaplint on GitHub diverge:

- The GitHub Action used in this template runs `@abaplint/cli` inside your own GitHub Actions workflow, on a standard GitHub-hosted runner. It is free, it works on private repositories, and it is MIT.
- The hosted `abaplint.app` GitHub App is freemium: free for public repositories, but a paid subscription for private ones, around US$19 per user per month at the time of writing. Check current pricing before you commit to it.

This template deliberately uses the free Action path, so the gate costs nothing even on a private repository.

## Setup

1. Copy `abaplint.json` from this folder into the root of your abapGit repository.
2. Copy `abaplint.yml` from this folder to `.github/workflows/abaplint.yml` in your repository. The copy in this kit is a template and is deliberately not placed at this kit's own active `.github/workflows/` path, so it never runs against the kit itself; it only becomes live once you copy it into your repo.
3. Set `syntax.version` in `abaplint.json` to your backend's SAP_BASIS release (see the mapping table below). The template ships `v758` (S/4HANA 2023).
4. Open a pull request. abaplint runs and annotates any findings inline.
5. Make it a real gate. In your repository, go to Settings, then Branches, and add a branch protection rule that requires the "abaplint (src/**)" check to pass before merge. Without this the check is advisory only.

For a local pre-flight before you push, run `npx @abaplint/cli` in the repository root; it uses the same `abaplint.json` and gives you the findings the PR would show. To produce a fresh default config to compare against, run `npx @abaplint/cli -d > abaplint.default.json` and diff it against your current `abaplint.json`.

## Pinning for supply-chain caution

The workflow references the action as `abaplint/actions-abaplint@main`, a moving reference, which is what abaplint's own documentation uses. If you prefer a fixed, auditable version, pin the action to a specific commit SHA, and optionally pin `@abaplint/cli` too with the `with: version:` field shown in the workflow's comment. That trades automatic updates for reproducibility; pick whichever fits your organisation's policy.

## Adapting the config

Change these fields to match your backend. Leave the rest of the template as-is unless you have a reason not to.

- **`syntax.version`**: set this to your backend's SAP_BASIS release. abaplint numbers its grammar to the release, so this affects which syntax it accepts. Never set "Cloud" on a classic on-stack system. Mapping to S/4HANA on-prem:

| abaplint version | S/4HANA on-prem |
|---|---|
| `v754` | 1909 |
| `v755` | 2020 |
| `v756` | 2021 |
| `v757` | 2022 |
| `v758` | 2023 |
| `v816` | 2025 |

  Older NetWeaver enum values also exist (`v700`, `v702`, `v740sp02/05/08`, `v750` to `v753`) if your backend predates S/4HANA.

- **`syntax.errorNamespace`**: the template ships `^(Z|Y)`. This makes abaplint "void", meaning silently accept, any standard SAP object it cannot resolve whose name falls outside this regex, so references to things like BU_PARTNER, VKONT_KK, or standard BAPI structures do not flood the report as "unknown type". Keep it narrow and matched to your custom namespaces; do not widen it to `.`, or you will void your own objects too.
- **`object_naming.clas` / `.intf`**: the template ships `^[ZY]` and `^[ZY]IF`, aligned with `errorNamespace` so both your Z and Y objects are checked. Tighten these to your own naming convention so the gate enforces it; if your shop uses only the Z namespace, `^Z` and `^ZIF` are equally valid.

Two things left deliberately off. Pure-formatting rules are omitted on purpose: abaplint here is scoped to correctness, Clean ABAP craft, naming, and size, and formatting is left to ATC on the system. And for a classic on-prem backend, keep `forbidden_void_type`, `no_prefixes`, `cloud_types`, and `strict_sql` off; they are aimed at ABAP Cloud and will produce a wall of noise against classic on-stack code.

## The gate can teach

A failing check is a signal, not just a blocker. When the same finding keeps coming back across pull requests, that is worth acting on: either turn it into a rule the gate enforces consistently, or fix the habit upstream so the class of issue stops arriving in the first place. Used this way, the gate gradually raises the floor rather than only policing it. Keep it proportionate; the aim is fewer recurring problems, not maximal strictness.

## Credits

abaplint and abapGit are both by Lars Hvam and Heliconia Labs. See abaplint.org and github.com/abaplint. The off-stack CI pattern this draws on was demonstrated by Philipp Doelker in "Off-Stack ABAP: a practical example".
