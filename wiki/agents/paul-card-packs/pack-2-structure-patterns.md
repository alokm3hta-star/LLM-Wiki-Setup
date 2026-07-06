# Paul Card Pack 2 - Critical Structure & Design Patterns (v2)

Scan Phase 2; write-mode: load iff the task writes or changes production code.
Read the core (`paul-dev-card.md`) first; its Intra-Card Precedence block wins on any conflict.
Rules moved verbatim from dev card v1 (2026-07-04 split); IDs stable; 4 documented merges - see core provenance note.

## Clean ABAP Rules (CA-*)

Apply to ABAP (and RAP method bodies) unless noted.

### Overview / adoption order
- **CA-OVERVIEW-02** The Methods section (do-one-thing, keep-methods-small) drives the most structural improvement.
- **CA-OVERVIEW-04** In legacy refactors, never mix old and new naming conventions within the same object.
- **CA-OVERVIEW-05** Boy Scout Rule: leave code a little cleaner than found.
- **CA-OVERVIEW-06** Build clean islands: make small components clean, use as tested refactoring baselines.

### Classes
- **CA-CLASSES-01** Prefer objects to static classes — statics can't be replaced by test doubles.
- **CA-CLASSES-04** Do not mix stateful and stateless design in the same class.
- **CA-CLASSES-05** Use global classes as default; local only where scope genuinely warrants it.
- **CA-CLASSES-06** Avoid deeply nested local class includes — hinders navigation/debugging, ABAP locks at include level.
- **CA-CLASSES-07** Make classes `FINAL` unless explicitly designed for inheritance.
- **CA-CLASSES-08** All members `PRIVATE` by default. (supersedes OOP-INHERIT-06)
- **CA-CLASSES-09** `PROTECTED` only when subclasses need to override.
- **CA-CLASSES-10** For post-construction-immutable objects, use `DATA ... READ-ONLY` instead of a getter.
- **CA-CLASSES-11** Use `READ-ONLY` sparingly — contradicts write-once-modify-never expectations from other languages. (supersedes OOP-ENCAP-04)
- **CA-CLASSES-12** Prefer `NEW` to `CREATE OBJECT` — shorter, chains.
- **CA-CLASSES-13** If a global class is `CREATE PRIVATE`, leave the `CONSTRUCTOR` public.
- **CA-CLASSES-14** Prefer multiple static creation methods to optional constructor parameters — ABAP has no overloading.
- **CA-CLASSES-15** Good creation-method prefixes: `new_`, `create_`, `construct_`.
- **CA-CLASSES-16** Singleton is the most overused/misapplied pattern — unexpected cross-effects, complicates testing.

### Methods
- **CA-METHODS-01** Call static methods via the class (`cl_x=>m( )`), never through an instance variable.
- **CA-METHODS-02** Access type definitions via the class/interface, not via an instance.
- **CA-METHODS-03** Prefer functional call syntax to `CALL METHOD`.
- **CA-METHODS-04** Omit `me->` unless resolving a local-variable/attribute name conflict.
- **CA-METHODS-05** Prefer instance to static methods — reflects object-hood, mocks more easily.
- **CA-METHODS-06** Public instance methods should always be part of an interface.
- **CA-METHODS-07** Aim for fewer than three `IMPORTING` parameters — combinatorial complexity.
- **CA-METHODS-08** Split methods instead of stacking `OPTIONAL` parameters.
- **CA-METHODS-09** Use `PREFERRED PARAMETER` sparingly — obscures which parameter is actually supplied.
- **CA-METHODS-10** A good method returns exactly one thing.
- **CA-METHODS-11** Prefer `RETURNING` to `EXPORTING` — functional style, chaining, avoids same-in/out errors.
- **CA-METHODS-12** Use `RETURNING` even for large tables — kernel-optimised; switch to `EXPORTING` only on measured evidence.
- **CA-METHODS-13** Do not mix `RETURNING`/`EXPORTING`/`CHANGING` in one method — signals it does more than one thing.
- **CA-METHODS-14** Use `CHANGING` sparingly — only for updating an existing, already-filled variable.
- **CA-METHODS-15** A Boolean input parameter usually signals the method does two things — split it.
- **CA-METHODS-16** Name a self-explanatory `RETURNING` parameter `RESULT`.
- **CA-METHODS-17** Clear or overwrite `EXPORTING` reference parameters — they may already hold data.
- **CA-METHODS-18** Never clear `VALUE` parameters (`RETURNING` is always `VALUE`).
- **CA-METHODS-19** "Do one thing" test: few params, no Booleans, one output, small, one abstraction level, one exception type, not further splittable.
- **CA-METHODS-20** A method implements the happy path OR handles errors, never both interleaved.
- **CA-METHODS-21** All statements in a method sit at the same abstraction level, one below the method itself.
- **CA-METHODS-22** Keep methods small — fewer than 20 statements, optimally 3-5.
- **CA-METHODS-23** Fail fast — validate and fail as early as possible.
- **CA-METHODS-24** `CHECK` vs `RETURN`: `CHECK` is shorter but its name hides what happens on failure.
- **CA-METHODS-25** `CHECK` inside a `LOOP` ends the current iteration only, not the loop/method — a common surprise.

### Error Handling
- **CA-ERRORS-01** Use `INTO DATA(message)` so messages are `SE91` where-used searchable.
- **CA-ERRORS-02** Prefer exceptions to return codes — handle at end of happy path via `CATCH`.
- **CA-ERRORS-03** When calling older return-code APIs (e.g. `BAPIRET2`), always check and raise if needed.
- **CA-ERRORS-04** Exceptions are for errors, not expected regular outcomes.
- **CA-ERRORS-05** Use class-based exceptions — never the outdated non-class-based `EXCEPTIONS ... OTHERS` pattern.
- **CA-ERRORS-06** Create your own abstract super classes per exception type, don't subclass foundation classes directly.
- **CA-ERRORS-07** Throw one type of exception — callers rarely need or can distinguish multiple.
- **CA-ERRORS-08** To let callers distinguish error situations, use sub-classes of one parent (or a typed error-code attribute).
- **CA-ERRORS-09** Throw `CX_STATIC_CHECK` for expected, reasonably handleable exceptions.
- **CA-ERRORS-10** Use `CX_NO_CHECK` for severe, unlikely-to-recover situations.
- **CA-ERRORS-11** `CX_DYNAMIC_CHECK` when the caller has full conscious control over whether it occurs.
- **CA-ERRORS-12** Dump only when certain no consumer can do anything useful afterwards.
- **CA-ERRORS-13** Prefer `RAISE EXCEPTION NEW` to `RAISE EXCEPTION TYPE ... EXPORTING`.
- **CA-ERRORS-14** Wrap foreign exceptions rather than letting them propagate unchanged (Law of Demeter).

## OOP / SOLID Rules (OOP-*)

- **OOP-SOLID-01/02** Single Responsibility: a class has exactly one reason to change; split bloated "does everything" classes.
- **OOP-SOLID-03/04** Open-Closed: open for extension, closed for modification — add behaviour via new classes.
- **OOP-SOLID-05/06/07** Liskov Substitution: a subclass must be usable wherever its superclass is, without invalidating superclass guarantees.
- **OOP-SOLID-08/09** Interface Segregation: many focused interfaces beat one general-purpose interface; don't force unused methods.
- **OOP-SOLID-10/11** Dependency Inversion: depend on abstractions, not concrete classes; high- and low-level modules both depend on abstractions.
- **OOP-ENCAP-01** Prefer `PRIVATE` attributes with `GET_*`/`SET_*`, enforcing consistency rules in setters.
- **OOP-ENCAP-02** Hide internal complexity behind simple public interfaces for testability/modifiability.
- **OOP-ENCAP-03** "Need-to-know" visibility: most attributes `PRIVATE`, state changes via validated setters, reads via getters.
- **OOP-ENCAP-05** Use `FRIENDS` sparingly — it deliberately bypasses standard access control.
- **OOP-INHERIT-01/05** Composition is generally preferred over inheritance — day-to-day default unless "is-a" is unambiguous. (supersedes CA-CLASSES-02)
- **OOP-INHERIT-02** Ideal hierarchy: Interface → (optional Abstract Class) → Concrete Class; challenge concrete-to-concrete inheritance.
- **OOP-INHERIT-03** Inheritance creates tight coupling — parent changes affect all children.
- **OOP-INHERIT-04** Apply the "is-a" test before choosing inheritance (`CashOrder` is-a `SalesOrder`).
- **OOP-POLY-01** Runtime dispatch is by actual object type, not declared variable type.
- **OOP-POLY-02** Use widening casts carefully — an incompatible dynamic type raises a runtime exception.
- **OOP-POLY-03** Interfaces for "secondary type"/cross-cutting ("is also") concepts, not the class's core "is-a" type.
- **OOP-INTERFACE-01** Default to interface-typed dependencies: expose a class consumed outside its own component through an interface (public static `CREATE` method + `CREATE PRIVATE` implementation), and declare consumers/collaborators against that interface type, never the concrete class — the standard SAP class-design pattern, and the mechanism behind both polymorphic substitution and test doubling.
- **OOP-EXCEPT-01** Keep a method's `RAISING` list small — too many suggests weak cohesion.
- **OOP-EXCEPT-02** Specific `CATCH` handlers must precede generic ones (runtime scans in order).
- **OOP-EXCEPT-03** Don't add/redefine methods on local exception classes.
- **OOP-LIFECYCLE-01** A constructor guarantees a consistent, valid initial state before the object reaches the caller.
- **OOP-LIFECYCLE-02** Keep constructor logic minimal, delegate to helpers, prefer factory methods over cluttered parameter lists.
- **OOP-LIFECYCLE-03** `CREATE {PUBLIC|PROTECTED|PRIVATE}` restricts instantiation to protect scarce/shared resources.
- **OOP-LIFECYCLE-04** Default to a factory class/static factory method for object creation rather than scattering `NEW`/`CREATE OBJECT` across consumers — it fulfils SRP for creation, centralises the class name used, and lets a double be substituted for isolated testing. Use as widely as the design tolerates; a plain value object with no swappable implementation is the main exception.
- **OOP-PACKAGE-01** Packages are black boxes exposing only a deliberate package interface.
- **OOP-PACKAGE-02** Common Closure Principle: objects in the same package should change for the same reasons.
- **OOP-PACKAGE-03** Static Dependencies Principle: packages with many incoming dependents must keep interfaces stable.
- **OOP-SYNTAX-01** Prefer generic ABAP types for reusable methods (one-task and minimal-params clauses: see CA-METHODS-19, CA-METHODS-07).
- **OOP-SYNTAX-02** "Find what varies and encapsulate it" from the start, or implementations swell unmanageably.

## TDD Rules (TDD-*)

### Class/interface design for testability
- **TDD-CLASSDESIGN-01** An interface's contract names what, not how, and concentrates on essentials.
- **TDD-CLASSDESIGN-02** ISP requires user-oriented interfaces — no more methods than users need, thematically grouped.
- **TDD-CLASSDESIGN-03** A framework's core mechanisms should define their own interfaces rather than depend on predefined ones (DIP).
- **TDD-CLASSDESIGN-04** Cohesion-graph model: nodes = methods/attributes, edges = every method-to-method/attribute dependency.
- **TDD-CLASSDESIGN-05** Split a class horizontally by abstraction level (delegate to an extracted lower class) or vertically by interface/role.
- **TDD-CLASSDESIGN-06** Coupling optimises independence between classes; cohesion optimises simplicity/reusability within one.
- **TDD-CLASSDESIGN-07** Keep a dependency internal unless the class is genuinely part of a framework.
- **TDD-CLASSDESIGN-08** Only put a dependency in a public signature if it serves broader/more flexible consumption.
- **TDD-CLASSDESIGN-09** Avoid premature optimisation — duplicates code/data, increases complexity; measure a mature version first.
- **TDD-CLASSDESIGN-11** Method parameter count should be zero or one where possible — 10+ params signals missing object grouping.
- **TDD-CLASSDESIGN-12** An object parameter replacing coupled primitives validates once at construction, not on every call.
- **TDD-CLASSDESIGN-14** Nested interfaces: each public method belongs to one role-specific interface; consumers depend only on their role's interface.
- **TDD-CLASSDESIGN-15** If only a few methods of an interface matter to each consumer, reconsider the interface's user groupings.
- **TDD-CLASSDESIGN-16** Class design pattern: an interface exposing all public methods, one or more named creation methods, `CREATE PRIVATE`/`PROTECTED`.
- **TDD-CLASSDESIGN-17** A constructor should only assign attributes — never call another class's static creation method directly.
- **TDD-CLASSDESIGN-18** Testable constructor design: protected constructor shared-only logic, side-effecting/test-hostile statements in a production-only `INIT` method.
- **TDD-CLASSDESIGN-20** Catalog pattern: a global base class with local subclasses, created via base-class public creation methods.
- **TDD-CLASSDESIGN-21** Adding a new entity type needs only a new subclass + factory method — no superclass/sibling changes (OCP).
- **TDD-CLASSDESIGN-22** Class friendship should be limited to a single class with narrow responsibility (e.g. factory-to-entity only).
- **TDD-CLASSDESIGN-23** Objects should use other objects, not multitudes of raw data.
- **TDD-CLASSDESIGN-24** Simple code requires not fearing future redesign — don't defensively over-prepare for eventualities that may not occur.

## Design Pattern Selection Index (DP-*)

27-pattern catalog (1 architectural + 7 creational + 9 structural + 10 behavioral). Consult before designing any multi-object structure.

**Architectural**
- **DP-01 MVC** — separate business logic from presentation/binding for GUI-style apps (ALV/WebDynpro/Fiori).

**Creational**
- **DP-02 Factory** — centralise multi-step object creation (config reads, auth checks, dynamic class determination) behind one static method.
- **DP-03 Abstract Factory** — a factory whose own logic must vary by runtime context, via a second abstraction layer over multiple concrete factories.
- **DP-04 Builder** — assemble an object from interchangeable parts step-by-step via a Director calling abstract build steps.
- **DP-05 Singleton** — exactly one instance per session, `CREATE PRIVATE` + static `get_instance`; avoid if independent state is needed.
- **DP-06 Multiton** — one cached instance per key, not one global instance.
- **DP-07 Lazy Initialization** — defer expensive-but-maybe-unneeded object creation to first access.
- **DP-08 Prototype** — clone an already-initialised instance when fresh construction is prohibitively slow.

**Structural**
- **DP-09 Adapter** — glue class translating calls between two incompatible interfaces.
- **DP-10 Bridge** — abstraction and implementation vary independently along two dimensions without class explosion.
- **DP-11 Composite** — recursive tree/parent-child structures (org units, BOMs, WBS) via common Leaf/Composite subclasses.
- **DP-12 DAO** — uniform access to the same conceptual data across multiple sources (DB vs external web service).
- **DP-13 Decorator** — wrap an object to add/restrict behaviour, same interface, chainable — the mechanism behind most SAP user-exits.
- **DP-14 Façade** — one simple orchestrating method over a complex subsystem, without blocking power-user bypass.
- **DP-15 Flyweight** — cache shared context-independent state via a factory; pass context-dependent state per call.
- **DP-16 Property Container** — a generic name-value attribute bag to extend a class without changing its signature.
- **DP-17 Proxy/Surrogate** — a same-interface wrapper intercepting calls for security/lazy-load/remote/logging; prefer when the target is `FINAL`.

**Behavioral**
- **DP-18 Chain of Responsibility** — request passes along a dynamically configurable handler chain (e.g. PO approval thresholds).
- **DP-19 Command** — encapsulate operations as objects for queuing/logging/undo; adds boilerplate, skip for simple one-shot calls.
- **DP-20 Mediator** — route n-object coordination through one hub instead of an n×n reference mesh; watch for the hub becoming a god object.
- **DP-21 Memento** — capture/restore full internal state (undo/redo) without external code reading its contents.
- **DP-22 Observer** — broadcast a subject's state change to a dynamic, decoupled subscriber set; new observers need no subject change.
- **DP-23 Servant** — shared helper logic for unrelated classes with no common ancestor that cannot be modified to add an `ACCEPT` method.
- **DP-24 State** — encapsulate each state as its own `FINAL` class, delegate via a context object, instead of scattered `CASE` blocks.
- **DP-25 Strategy** — swap interchangeable algorithms at runtime via composition; prefer once >2-3 variants exist.
- **DP-26 Template Method** — `FINAL` skeleton + `ABSTRACT` steps for a fixed algorithm with per-subclass variation (Hollywood Principle).
- **DP-27 Visitor** — add new operations to a stable hierarchy via new visitor classes, without modifying existing classes (clear OCP demonstration).
