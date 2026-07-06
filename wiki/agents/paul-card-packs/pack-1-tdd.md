# Paul Card Pack 1 - TDD & Test Conformance (v2)

Scan Phase 1; write-mode: load iff the task writes or changes test code.
Read the core (`paul-dev-card.md`) first; its Intra-Card Precedence block wins on any conflict.
Rules moved verbatim from dev card v1 (2026-07-04 split); IDs stable.

## Clean ABAP Rules (CA-*)

### Testing
- **CA-TESTING-01** Write all code in a way that allows automatic testing.
- **CA-TESTING-02** Enable others to mock you: interfaces at outward-facing places, helpful doubles, dependency inversion.
- **CA-TESTING-03** Make test code even more readable than production code.
- **CA-TESTING-04** Automate manual test reports as unit tests with `CL_ABAP_UNIT_ASSERT`.
- **CA-TESTING-05** Unit tests validate only the public interface.
- **CA-TESTING-06** Coverage exists to find untested code, not to meet a KPI.
- **CA-TESTING-07** Name local test classes by the "when" or "given" part of the story.
- **CA-TESTING-08** Unit tests belong in the local test include of the class under test.
- **CA-TESTING-09** Shared test helper methods belong in a dedicated help class.
- **CA-TESTING-10** Default to `cut` (Code Under Test) if no meaningful CUT name exists.
- **CA-TESTING-11** Declare the code under test with an interface type, not a class type.
- **CA-TESTING-12** Extract calls needing many parameters to a defaulting helper method.
- **CA-TESTING-13** Inject dependencies via the constructor, not setters or `FRIENDS`.
- **CA-TESTING-14** Setter injection is an anti-pattern — enables unexpected multiple setter calls.
- **CA-TESTING-15** Consider `CL_ABAP_TESTDOUBLE` over hand-written custom double classes.
- **CA-TESTING-17** For `CREATE PRIVATE` CUTs, use `LOCAL FRIENDS` to call the constructor with a double.
- **CA-TESTING-18** Don't use `LOCAL FRIENDS` to set private members directly — fragile to internal structure changes.
- **CA-TESTING-19** Never add production code solely for automated tests.
- **CA-TESTING-20** Never subclass the CUT and override methods to mock them.
- **CA-TESTING-21** Set up only the data/mocks actually needed for the test.
- **CA-TESTING-22** Unit tests are data-in-data-out — don't build test frameworks.
- **CA-TESTING-23** Test method names reflect the given and expected outcome.
- **CA-TESTING-24** Structure every test method: given (initialise), when (call), then (assert).
- **CA-TESTING-25** The "when" section is exactly one call to the code under test.
- **CA-TESTING-26** `TEARDOWN` only when cleaning up DB entries/external resources in integration tests.
- **CA-TESTING-27** Use obviously meaningless but clearly labelled test data.
- **CA-TESTING-28** Make test-data differences easy to spot, not buried in long strings.
- **CA-TESTING-29** Use named constants to explain the role test data plays.
- **CA-TESTING-30** Few, focused assertions per test method.
- **CA-TESTING-31** Use the most specific assertion type available.
- **CA-TESTING-32** Assert actual expected content, not item count.
- **CA-TESTING-33** For a meta-quality (length, ordering), assert the quality directly, not exact content.
- **CA-TESTING-34** Use `cl_abap_unit_assert=>fail( )` for expected-exception checks.
- **CA-TESTING-35** Declare unexpected exceptions in `RAISING` and let them propagate — don't catch-and-fail.
- **CA-TESTING-36** Extract repeated assertion logic into named custom-assert helper methods.

## TDD Rules (TDD-*)

### Test design
- **TDD-DESIGN-01** Black box (external), white box (unit, internal), grey box (isolated component/acceptance) — grey box is the "golden mean".
- **TDD-DESIGN-02** Equivalence classes must include invalid-entry classes, not just valid ones.
- **TDD-DESIGN-03** Boundary-value testing: error probability peaks at class boundaries — test both sides plus a representative.
- **TDD-DESIGN-04** Decision tables (≤4 params): one row per case, given/when/then columns.
- **TDD-DESIGN-05** All-pair testing for many parameters — every value-pair once, catches 70-90% of errors empirically.
- **TDD-DESIGN-06** State-oriented testing: state/event/action-and-successor-state table, given-when-then rows.
- **TDD-DESIGN-07** New development: prioritise isolated testing from scratch.
- **TDD-DESIGN-08** Coverage KPIs are a unit-test responsibility — don't chase them with a few large component/acceptance tests.
- **TDD-DESIGN-09** Given/When/Then: given assembles the initial situation; when calls the method; then verifies output/state/spy calls.
- **TDD-DESIGN-10** Test methods are living, executable documentation — intolerant of spec drift.
- **TDD-DESIGN-11** Cohesion peaks when a test class tests exactly one product method.
- **TDD-DESIGN-12** Wrap the method under test in a simplified `SIMPLE_MUT` helper for output capture.
- **TDD-DESIGN-13** FIRST: Fast, Independent, Repeatable, Self-validating, Timely.
- **TDD-DESIGN-14** SOLID applies to test-code design as much as production code — see OOP-SOLID-* in pack 2.
- **TDD-DESIGN-15** Prioritise building test infrastructure over raw coverage — infrastructure lets coverage be added efficiently later.
- **TDD-DESIGN-16** Red-green-refactor: write only enough test to expose incompleteness, only enough code to pass, then improve in small steps.
- **TDD-DESIGN-17** Baby-step principle: each new test method introduces exactly one new aspect.
- **TDD-DESIGN-18** Under time pressure, prioritise test quality over quantity — infrastructure first, coverage second.
- **TDD-DESIGN-19** Test relations deliberately avoid a product-to-test dependency (would cycle back through test-only components).
- **TDD-DESIGN-20** One-assertion-per-test is a rule of thumb, not absolute — justified exceptions exist when several distinct behaviours are checked together.

### Test doubles
- **TDD-DOUBLE-01** Interface double (`DOM` on an interface) vs subclass double (`DOM` redefining a protected method) — pick per situation.
- **TDD-DOUBLE-02** Prefer a proxy class over a proxy method — isolates multiple FMs, reusable, avoids SRP violation.
- **TDD-DOUBLE-03** Legacy code (Feathers's definition) often lacks testable `MUT`-`DOM` interaction by construction.
- **TDD-DOUBLE-04** Constructor injection via `CREATE`, stored in a private attribute, is the most common mechanism.
- **TDD-DOUBLE-05** Backdoor injection (local friendship) restricted by convention to injection or calling a nonpublic method under test — never inspecting other state.
- **TDD-DOUBLE-06** Reset static factory doubles in `SETUP` — otherwise the productive factory serves the double to every caller.
- **TDD-DOUBLE-07** Front-door injection is uncritical; back-door injection is acceptable despite redesign risk (dependencies of the front-door-only alternative are far higher).
- **TDD-DOUBLE-08** Six categories of dependency motivate test isolation: data accuracy, other-parts existence/correctness, controllable behaviour, cost/side-effects, execution time, error-localisation cost.
- **TDD-DOUBLE-09** A test is valuable only if run regularly and its failure reliably indicates a real error.
- **TDD-DOUBLE-10** Test stub: passes appropriate indirect-input data to the method under test.
- **TDD-DOUBLE-11** Test spy: caches indirect output of `MUT`'s call to `DOM` for later verification.
- **TDD-DOUBLE-12** Mock object: expected call data set up front, verifies inline — coding one by hand is rare.
- **TDD-DOUBLE-13** Fake object: factor extensive simulation state/behaviour into its own (promotable) local class.
- **TDD-DOUBLE-14** Dummy object: never actually called, exists only so `MUT` can verify a reference is bound.
- **TDD-DOUBLE-15** Build a minimal test double by running the test repeatedly and implementing only what each failure demands.
- **TDD-DOUBLE-16** Double-class creation methods should return the double's own type, not the interface type, for assertion-helper access.
- **TDD-DOUBLE-17** A help class must not redefine any productive method — would skew test results.
- **TDD-DOUBLE-19** `ANY`/`OTHER`/`FURTHER` constants denote arbitrary, mutually-distinct values when a test cares only about value difference, not a specific value.
- **TDD-DOUBLE-20** Implement only the interface methods the test actually exercises.
- **TDD-DOUBLE-21** `CRT_` (not `CREATE_`) frees identifier characters for a descriptive creation-method name.
- **TDD-DOUBLE-22** A single generic `CREATE_DOUBLE(4 optional params)` is compact but gives no guidance on valid combinations — prefer named creation methods.
- **TDD-DOUBLE-23** Prefer a `DO_` prefix over a `_DOUBLE` suffix — the double property should lead.
- **TDD-DOUBLE-24** Uninjected double attributes should error at call time, intentionally surfacing missing isolation.
- **TDD-DOUBLE-25** Demand-driven isolation: don't double every method upfront, only where its absence causes false alarms.
- **TDD-DOUBLE-26** A configured (not coded) double publishes variability via a getter so new cases don't require class changes.
- **TDD-DOUBLE-27** Publishing an API with its global double is a low-effort cross-team isolation model.
- **TDD-DOUBLE-28** A test data class must behave identically to its productive superclass (no redefinitions) — isolation is not its job.

### Test isolation
- **TDD-ISOLATION-01** The Open SQL Test Double Framework is primarily a stub, rarely a spy, never a mock.
- **TDD-ISOLATION-02** Test seams are for otherwise-untestable legacy code only — new development uses interface/factory testability.
- **TDD-ISOLATION-03** The ABAP Test Double Framework violates SRP by pushing double-class responsibility into the test class.
- **TDD-ISOLATION-04** Clean test code is impossible without an application-specific test infrastructure.
- **TDD-ISOLATION-05** Isolated tests beat integration tests on speed, flexibility, and error localisation.
- **TDD-ISOLATION-06** For new development, isolated tests cost no more than non-isolated ones if classes are already cohesive/decoupled.

### ABAP Unit framework
- **TDD-FRAMEWORK-01** Lifecycle: `CLASS_SETUP` once → per-method `SETUP`/test/`TEARDOWN` → `CLASS_TEARDOWN` once; runner issues `ROLLBACK WORK` unless `COMMIT WORK` was called.
- **TDD-FRAMEWORK-02** Test-method execution order is unspecified — avoid inter-test dependencies.
- **TDD-FRAMEWORK-03** All test-class methods should be private — only the runner calls them.
- **TDD-FRAMEWORK-04** Prefer a help subclass over local friendship — friendship "opens the door" to unnoticed extra dependencies.
- **TDD-FRAMEWORK-05** `CL_AUNIT_ASSERT` is obsolete — use `CL_ABAP_UNIT_ASSERT`.
- **TDD-FRAMEWORK-06** Every test class declares `RISK LEVEL` (HARMLESS/DANGEROUS/CRITICAL) and `DURATION` (SHORT/MEDIUM/LONG).
- **TDD-FRAMEWORK-07** `RISK LEVEL` cannot relax down a hierarchy (same or escalate only); `DURATION` may loosen freely.
- **TDD-FRAMEWORK-08** Subclass `SETUP` does not explicitly call superclass `SETUP` — the runner invokes both in the correct order.
- **TDD-FRAMEWORK-09** Global test classes must be abstract — only local test classes are concrete.
- **TDD-FRAMEWORK-10** Keep test-related classes local until reuse genuinely demands globalising them.

### Naming/comment conventions
- **TDD-CONVENTIONS-01** A wrong comment is worse than a missing one — wastes time and erodes trust.
- **TDD-CONVENTIONS-02** Replace a "what does this block do" heading comment by extracting a descriptively named help method.
- **TDD-CONVENTIONS-03** Wrap complex Boolean expressions in `IS_XXX`/`HAS_XXX` (product/test) or `ASSERT_XXX` (test verification) helpers.
- **TDD-CONVENTIONS-05** Law of Demeter: call only your own class/superclass methods, or methods of objects you created or received directly — never chain through a retrieved object.
- **TDD-CONVENTIONS-06** Prefer functional notation with inline declaration over classical `CALL METHOD ... RECEIVING`.
- **TDD-CONVENTIONS-07** Class/interface/exception/test-artefact prefixes: `CL_`/`LCL_`, `IF_`/`LIF_` (`_C` suffix for constants-only), `CX_`/`LCX_`, `TC_`/`LTC_`, `TD_`/`LTD_`, `TH_`/`LTH_`, `TS_`/`LTS_`.
- **TDD-CONVENTIONS-08** Storage prefixes: `S` static, `M` instance, `D` double, `I`/`E`/`C`/`R` param kinds, `G` global var, `L` local var. **Superseded for new code by Precedence #1** (no storage prefixes on production variables); retained only for decoding older example code.
- **TDD-CONVENTIONS-09** `CREATE_` for object creation, `GET_` for singleton retrieval.
- **TDD-CONVENTIONS-10** Local-vs-global test-artefact naming table: `LTC_A`/`TC_APPL_A`, `LTD_B`/`TD_APPL_B`, `LTH_C`/`TH_APPL_C`, `LTS_D`/`TS_APPL_D`.

### Test data & infrastructure
- **TDD-DATA-01** Test-class attribute prefixes: `IMPORT`/`IMP` (input), `ACTUAL`/`ACT` (output), `ASSERT` (verification methods).
- **TDD-DATA-02** This test-class pattern avoids the obscure-test antipattern and satisfies SRP (one class per complex product method).
- **TDD-DATA-03** Test Data Containers (TDC) are worthwhile only for many cases of a standardised process — rarely for unit tests.
- **TDD-DATA-04** `QUIT = IF_AUNIT_CONSTANTS=>NO` lets a data-driven loop continue past one variant's assertion failure.
- **TDD-DATA-05** Cascading comparison follows the subsidiarity principle — each object compares only its own data, delegates the rest.
- **TDD-DATA-06** Separate creation from assignment (static creator + `ADD_ITEM`) to comply with OCP.
- **TDD-DATA-07** This test-data pattern's cost: productive classes can't be `FINAL`, state attributes only `PROTECTED`.
- **TDD-DATA-08** Base class: everything derived classes need sits in public/protected; the runner-called setup stays private.
- **TDD-DATA-09** Test case superclass pattern: base-class help methods form a "test language" that new test methods extend.
- **TDD-DATA-10** A test suite is robust if it runs independently and produces no false positives.
- **TDD-DATA-11** Test data containers hide detail from the reader (obscure-test antipattern) — prefer visible creation methods where readability matters.
- **TDD-DATA-12** Repeatability means running multiple times AND in a fresh system with no preconditions (incl. after transport).
- **TDD-DATA-13** Six test-infrastructure components: Creation, Generation, Simplification, Isolation, Simulation, Organization.
- **TDD-DATA-14** For good coverage, expect at least as much test code as product code.

### Acceptance / integration tests
- **TDD-ACCEPTANCE-01** ATDD is top-down for test definition (acceptance→component→unit), bottom-up for implementation (divide-and-conquer).
- **TDD-ACCEPTANCE-02** Stateless factories: inject once in `class_setup`. Stateful-singleton factories: `GET_NEW` per test method.
- **TDD-ACCEPTANCE-03** Avoid round trips (verifying one method via another of the same class) in unit tests unless unavoidable.
- **TDD-ACCEPTANCE-06** Test-penetration width reflects the product code under test, not the isolation doubles used.
- **TDD-ACCEPTANCE-07** A `CREATE_GIVEN`-style helper should return a different ID each call, improving test-method independence.
- **TDD-ACCEPTANCE-08** A package with a minimal (single) interface lets one global double achieve complete isolation.
- **TDD-ACCEPTANCE-09** Unit-test-level decisions are deliberately left to individual developers, not the team-wide test strategy.

### Refactoring & package design
- **TDD-REFACTOR-01** Extracting repeated startup statements into `SETUP` (with constants) serves DRY.
- **TDD-REFACTOR-02** KISS counterbalances extreme compactness — not always more readable, especially for newer developers.
- **TDD-REFACTOR-03** Only add speculative constants/combinations on actual demand — idle code obscures current state.
- **TDD-REFACTOR-04** A package interface should expose interfaces plus a factory class only, never regular classes.
- **TDD-REFACTOR-05** Dependency inversion applies at package level too — a framework package defines its own interfaces.
- **TDD-REFACTOR-06** A package's primary tasks: modularisation, encapsulation, decoupling.
- **TDD-REFACTOR-07** Outsourcing test code to its own package avoids long transport-correction-instruction chains.
- **TDD-REFACTOR-08** Legacy-code isolation costs more upfront but pays off in the medium term almost always.
