# Paul Dev Card (v2) - core

Hand-stored, read at spawn. This core is the always-loaded protocol layer for craft conformance (Clean ABAP / OOP-SOLID / TDD / design-pattern selection); every rule body lives in the three phase packs under `paul-card-packs/` (Pack Index below). It does not replace the full Paul spec or live lookup for anything not covered here. Conventions: core+packs layout, ID stability and tombstones (Dev-card convention).

## Pack Index & Loading Rules

| Pack file | Rule families | ~Tokens | Scan phase | Write-mode load rule |
|---|---|---|---|---|
| `paul-card-packs/pack-1-tdd.md` | CA-TESTING; TDD-DESIGN/DOUBLE/ISOLATION/FRAMEWORK/CONVENTIONS/DATA/ACCEPTANCE/REFACTOR | ~5.0k | Phase 1: TDD / test conformance | Load iff the task writes or changes test code |
| `paul-card-packs/pack-2-structure-patterns.md` | CA-OVERVIEW/CLASSES/METHODS/ERRORS; OOP-*; TDD-CLASSDESIGN; DP-* index | ~4.6k | Phase 2: critical structure & design-pattern fit | Load iff the task writes or changes production code |
| `paul-card-packs/pack-3-naming-readability.md` | CA-NAMES; CA-FORMAT content rules (01, 03-13, 15-17); CA-CONDITIONS; CA-CONST; CA-TABLES | ~1.8k | Phase 3: naming / readability | Load iff the task creates new named objects or readability polish is requested |

Loading rules: **when in doubt, load the pack**. Scan mode (`@paul scan`) loads this core plus the named phase pack exactly. Write mode follows the Packs column in Task Classification below. Formatting has no pack or phase; it is ATC's job (see Enforcement). Core precedence wins over pack text (Intra-Card Precedence below).

## Escalation Protocol

1. Consult this card's rules that match the task's stack (ABAP / RAP / CAP) and object type first — this card is a craft-rules cache, not a substitute for grounding a specific SAP fact.
2. Apply this card's rules that match the task's stack (ABAP / RAP / CAP) and object type. Cite rule IDs in the hand-off, not full quotes.
3. **Bounded reading**: at most 3 craft deep-dives (full page reads beyond this card) per task. If a 4th is needed, note it as a card gap rather than reading further ungoverned.
4. If a rule here conflicts with an explicit user instruction for this task, follow the user and note the deviation with the rule ID in the hand-off.
5. If no rule here covers the situation, follow the Extraction-Request Protocol (final resort) in the full Paul spec — do not guess a convention.

## Intra-Card Precedence (2026-07-03)

The card distils craft rules that disagree in places. Where two rules conflict, this block wins. General rule: **CA-*** (official Clean ABAP style) governs production-code style; **TDD-*** governs test-infrastructure design. Explicit resolutions:

1. **Variable prefixes**: production variables carry **no** Hungarian/storage prefixes — CA-NAMES-01/14 win (user-confirmed 2026-07-03). TDD-CONVENTIONS-08's storage prefixes are superseded for new code; TDD-CONVENTIONS-07/10's object-type and test-artefact prefixes (`CL_`/`IF_`/`LTC_`/`LTD_`/`LTH_`/`LTS_`) are not Hungarian encoding and remain in force.
2. **Test-double tooling**: default `CL_ABAP_TESTDOUBLE` for simple interface stubbing (CA-TESTING-15); switch to a hand-written double class (TDD-DOUBLE-*) when the double needs its own state, assertion helpers, or cross-test reuse (TDD-DOUBLE-16). TDD-ISOLATION-03's SRP criticism is the trigger for that switch, not a ban on the framework.
3. **Constructor visibility**: default `CREATE PRIVATE` + public constructor (CA-CLASSES-13); use a protected constructor (TDD-CLASSDESIGN-18) only when the class is deliberately designed for subclass test doubles.
4. **`LOCAL FRIENDS`**: prefer a help subclass for member access (TDD-FRAMEWORK-04); `LOCAL FRIENDS` only for constructor injection into a `CREATE PRIVATE` CUT (CA-TESTING-17), never to read or set private state (CA-TESTING-18, TDD-DOUBLE-05).
5. **Creation-method naming**: `create_` is the default (identical to TDD-CONVENTIONS-09's `CREATE_` — ABAP is case-insensitive); CA-CLASSES-15's `new_`/`construct_` are acceptable variants; `CRT_` (TDD-DOUBLE-21) applies inside double classes only.

## Enforcement — verify, don't memorise

The full Paul spec already mandates the loop: RED (`abap_run_unit_tests`) → implement → activate → GREEN → refactor per this card → `abap_run_atc` + `abap_atc_get_result` → `abap_atc_execute_deterministic_quickfixes`, remainder fixed manually or justified. The mechanical layout rules (CA-FORMAT-14, CA-FORMAT-18 through CA-FORMAT-33) are **toolchain-verified** by that ATC pass: write naturally, then fix findings — do not spend generation-time attention self-policing them. The Pre-Handoff Checklist (end of card) covers the high-impact rules ATC cannot check. CA-FORMAT-14 and CA-FORMAT-18 through 33 are retired from the packs to this ATC delegation; the IDs remain reserved and are never reused.

## Task Classification

| Task type | Packs to load |
|---|---|
| **Grounding/planning task** (no code written). | core only (~2.8k) |
| **Small task** (single method/class edit, no new object): card only, ≤5 reads, skip the deep-dive budget. | core + pack 2 (~7k); add pack 1 if tests are touched (~11.5k) |
| **Standard task** (new class/interface, new test suite): card + up to 3 deep-dives for the specific rule families in play. | core + all packs (~13.4k) |
| **Pattern-warranting task** (multiple interacting objects, extensibility requirement, cross-cutting concern): consult the Design Pattern Selection Index in pack 2 before designing the class structure; cite the chosen DP-ID in the hand-off. | core + all packs (~13.4k) |
| **RAP/CAP task**: apply the ABAP-general rules (naming, error handling, testing discipline) plus the stack-specific KNOWLEDGE GAP caveats below — RAP/CAP-specific craft coverage in this card is thin. | core + all packs (~13.4k) |

## Per-Stack Applicability

- **ABAP**: full CA-*/OOP-*/TDD-*/DP-* coverage applies directly.
- **RAP**: CA-*/OOP-*/DP-* apply to behaviour-implementation classes; TDD-FRAMEWORK-*/TDD-DOUBLE-* apply conceptually but the concrete behaviour-test-double API is a KNOWLEDGE GAP (see below) — ground any specific `cl_abap_behv_test_environment` signature via [MCP] or [SAP] before use, never guess it from this card.
- **CAP**: CA-*/TDD-DESIGN-*/TDD-ACCEPTANCE-* concepts (given-when-then, FIRST, isolation-by-category) transfer; the ABAP-syntax-specific rules (CA-METHODS/CA-TABLES/TDD-FRAMEWORK ABAP-Unit-lifecycle rules) do not apply. Concrete `cds.test`/Jest coverage patterns are a KNOWLEDGE GAP (see below).

## KNOWLEDGE GAP rows

- **ABAP CDS DDL comment syntax** — no grounded page states the comment character(s) for a CDS view-entity (`.ddls`) source. Behavior Definition Language uses `//` line / `/* ... */` block comments, but that is a different language from CDS view entities; don't carry it over. Don't assume CA-FORMAT-06's `"` convention applies either. Ground via `[SAP]` published CDS docs before writing a comment in a `.ddls` file.
- **`cds.test` (CAP testing framework)** — no grounded page covers its API/assertion surface in depth. Do not invent test syntax; ground via published npm/`@sap/cds` docs `[SAP]` or flag as an honest stub.
- **`cl_abap_behv_test_environment` (RAP behaviour-test doubles)** — no grounded page covers its concrete API (double injection, EML mocking surface). Do not invent method signatures; verify via `[MCP]` introspection if the live ADT MCP server exposes it, else `[SAP]` published docs, else extraction request.

## Reuse Ladder (before writing ANY code)
Climb in order; stop at the first rung that answers. Lazy about the solution, never about the grounding.
1. Does this object/method need to exist at all? (YAGNI — if the test does not demand it, do not write it.)
2. Does the codebase already show an existing custom Z*/Y* object or pattern that does it? [T1] — reuse/extend it.
3. Does a released SAP API or XCO library call do it? [T1/T2] — call it.
4. Does a RAP framework mechanism (determination, validation, draft handling, feature control) do it? — configure, do not code.
5. Is it one statement? Write one statement.
6. Only then: the minimum implementation that makes the failing test pass.
Never traded away: error handling, authority checks, input validation, TDD discipline, grounding citations.

## Pre-Handoff Checklist (MUST — re-read before every hand-off)

The rules with the highest defect impact that the ATC pass cannot verify and that differ most from generic coding instincts. Check each against the produced code; cite any deviation with its rule ID in the hand-off.

1. Every public instance method sits behind an interface; consumers and the test CUT are declared on the interface type, not the class (CA-METHODS-06, OOP-INTERFACE-01, CA-TESTING-11).
2. Objects are created via a factory or named static creation method; classes are `CREATE PRIVATE`; no bare `NEW` scattered across consumers (OOP-LIFECYCLE-04, TDD-CLASSDESIGN-16).
3. Classes `FINAL` unless designed for inheritance; all members `PRIVATE` by default (CA-CLASSES-07/08).
4. Dependencies injected via the constructor only — no setter injection (CA-TESTING-13/14).
5. One output per method: `RETURNING`, named `RESULT`; never mixed with `EXPORTING`/`CHANGING` (CA-METHODS-11/13/16).
6. No Boolean input parameters — split the method instead (CA-METHODS-15).
7. Methods under 20 statements, one abstraction level, happy path not interleaved with error handling (CA-METHODS-20/21/22).
8. Class-based exceptions only; one exception type per method (CA-ERRORS-05/07).
9. Booleans are `abap_bool` with `abap_true`/`abap_false`, set via `xsdbool( )` (CA-TABLES-11/12/13).
10. Every test method is given/when/then with exactly one CUT call in the "when" (CA-TESTING-24/25).
11. Test artefacts follow `LTC_`/`LTD_`/`LTH_`/`LTS_` naming; every test class declares `RISK LEVEL` and `DURATION` (TDD-CONVENTIONS-07/10, TDD-FRAMEWORK-06).
12. Production variables carry no storage prefixes (Precedence #1); no production code exists solely for tests (CA-TESTING-19).

Then confirm the spec's loop closed: GREEN `abap_run_unit_tests` and the `abap_run_atc` result are both cited in the hand-off.

## Provenance

Authored 2026-07-03; rule IDs are stable forever: never renumbered, never reused.

**Revision (v2 split, 2026-07-04)**: card split into this core plus 3 phase packs under `paul-card-packs/`; rule text moved verbatim. Pruned/merged in the split: CA-FORMAT-14 and CA-FORMAT-18 through 33 retired to the Enforcement ATC delegation; CA-CLASSES-02 superseded by OOP-INHERIT-01/05; OOP-INHERIT-06 superseded by CA-CLASSES-08; OOP-ENCAP-04 superseded by CA-CLASSES-11; OOP-SYNTAX-01 trimmed to its generic-types clause; CA-NAMES-05 dropped; CA-FORMAT-02 merged into CA-NAMES-02. Rule IDs are stable forever: never renumbered, never reused.
