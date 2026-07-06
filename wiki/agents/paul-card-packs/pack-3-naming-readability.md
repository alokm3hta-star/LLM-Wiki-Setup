# Paul Card Pack 3 - Naming & Readability (v2)

Scan Phase 3; write-mode: load iff the task creates new named objects or readability polish is requested.
Read the core (`paul-dev-card.md`) first; its Intra-Card Precedence block wins on any conflict.
Rules moved verbatim from dev card v1 (2026-07-04 split); IDs stable; CA-FORMAT-14/18-33 retired to core Enforcement; CA-NAMES-05 dropped, CA-FORMAT-02 merged into CA-NAMES-02.

## Names

- **CA-NAMES-01** Names convey content/meaning, not data type or technical encoding.
- **CA-NAMES-02** Do not fix a bad name with a comment — rename it. (supersedes CA-FORMAT-02)
- **CA-NAMES-03** Use solution/problem-domain terms shared with product owners and customers, not a private vocabulary.
- **CA-NAMES-04** Use plural for collections (`countries`, not SAP-legacy singular `country`).
- **CA-NAMES-06** Use `snake_case` consistently (ABAP is case-insensitive).
- **CA-NAMES-07** Write names in full where space allows — avoid abbreviations.
- **CA-NAMES-08** When abbreviating, use the same abbreviation for the same concept everywhere.
- **CA-NAMES-09** Nouns for classes/interfaces/objects; verbs for methods.
- **CA-NAMES-10** Boolean methods use `is_`/`has_` prefixes.
- **CA-NAMES-11** Omit noise words ("data", "info", "object") that add no information.
- **CA-NAMES-12** One word per concept — pick a term and stick to it.
- **CA-NAMES-13** Don't name a class after a pattern (`file_factory`) unless it genuinely implements it.
- **CA-NAMES-14** Remove all Hungarian-notation-style encoding prefixes.
- **CA-NAMES-15** A method named identically to a built-in function (`condense`, `lines`, `strlen`) always shadows it — avoid.

## Comments & Formatting

- **CA-FORMAT-01** Express yourself in code, not comments — natural-reading code needs no explanation.
- **CA-FORMAT-03** Extract named methods to show structure rather than using comment separators.
- **CA-FORMAT-04** Comments explain why, never restate the code in natural language.
- **CA-FORMAT-05** Long design-intent comment blocks on a class signal a design problem — design belongs in design docs.
- **CA-FORMAT-06** Comment with `"`, not `*` — quote-comments indent with the code. Applies to classic/OO ABAP only; ABAP CDS DDL comment syntax is a KNOWLEDGE GAP (see the core) — don't assume this carries over into a `.ddls` file.
- **CA-FORMAT-07** Place a comment on the line before the statement it explains, not after.
- **CA-FORMAT-08** Commented-out code is an anti-pattern — delete it.
- **CA-FORMAT-09** No manual versioning in comments — transport order texts are the right place.
- **CA-FORMAT-10** `FIXME`/`TODO`/`XXX` markers must carry the author's user ID/initials.
- **CA-FORMAT-11** No method signature/end-of comment blocks — a printout-era artefact.
- **CA-FORMAT-12** Don't duplicate message texts as comments — extract a descriptively named method instead.
- **CA-FORMAT-13** Write ABAP Doc only for APIs consumed by other teams/applications.
- **CA-FORMAT-15** Apply the same formatting style project-wide.
- **CA-FORMAT-16** Optimise for reading, not writing — code is read far more often. Holds regardless of who authored it: Paul's write cost is near-zero, so almost the entire lifetime cost of a change is the human review/maintenance that follows — that sharpens this rule for AI-authored code, not weakens it.
- **CA-FORMAT-17** Apply the ABAP Pretty Printer before activating any object. Paul works headless and his toolchain exposes no formatter action — so Paul must instead satisfy this section's layout rules (indentation, spacing, line breaks, 120-char limit) directly in the source it writes before activation.

## Conditions & Ifs

- **CA-CONDITIONS-01** Prefer positive conditions — easier to read.
- **CA-CONDITIONS-02** Prefer `IS NOT` to `NOT IS` — negation needs a mental turnaround.
- **CA-CONDITIONS-03** Consider predicative Boolean method calls (`IF condition_is_fulfilled( )`).
- **CA-CONDITIONS-04** Decompose complex conditions into named Boolean variables.
- **CA-CONDITIONS-05** Extract complex conditions into dedicated Boolean methods.
- **CA-CONDITIONS-06** No empty `IF` branches — invert the condition so logic sits in the positive case.
- **CA-CONDITIONS-07** Prefer `CASE` to `ELSEIF` chains for mutually exclusive alternatives.
- **CA-CONDITIONS-08** Keep `IF` nesting depth low — complexity grows exponentially.
- **CA-CONDITIONS-09** Prefer simpler methods to regular expressions for simple cases.
- **CA-CONDITIONS-10** Check for an SAP basis function before writing a validation regex.
- **CA-CONDITIONS-11** Build genuinely complex regexes from named sub-expressions.

## Constants & Variables

- **CA-CONST-01** Use named constants instead of magic numbers — intent + searchability.
- **CA-CONST-02** Name constants by meaning, not value.
- **CA-CONST-03** Prefer `ENUM` to constants interfaces — an interface implies "implementable", misleading.
- **CA-CONST-04** Without `ENUM`, at least group related constants in `BEGIN OF ... END OF`.
- **CA-CONST-05** Declare variables inline at first use.
- **CA-CONST-06** Don't exploit a variable's scope beyond its statement block — confuses readers.
- **CA-CONST-07** Don't chain up-front `DATA:`/`FIELD-SYMBOLS:` declarations — implies a false relatedness; one declaration per line.
- **CA-CONST-08** Modern expression syntax (2021+) replaces most field-symbol use cases for dynamic access.
- **CA-CONST-09** Choose the right loop target: field symbol (`ASSIGNING`), data reference (`REFERENCE INTO`), or data object (`INTO`).

## Tables, Strings, Booleans

- **CA-TABLES-01** Choose table type deliberately — hash overhead pays off only for large data with many reads.
- **CA-TABLES-02** Avoid `DEFAULT KEY` — often added just to make functional syntax compile.
- **CA-TABLES-03** Prefer `INSERT VALUE #(...) INTO TABLE` to `APPEND TO`.
- **CA-TABLES-04** Prefer `line_exists( )` to `READ TABLE`/`LOOP AT` for existence checks.
- **CA-TABLES-05** Prefer `READ TABLE ... REFERENCE INTO` to a `LOOP AT ... EXIT` for single-entry reads.
- **CA-TABLES-06** Prefer `LOOP AT ... WHERE` to a nested `IF`/`EXIT`.
- **CA-TABLES-07** Avoid unnecessary table reads — read once, react to the exception if a row is expected.
- **CA-TABLES-08** Use backtick string literals — single-quote adds a superfluous `CHAR` conversion.
- **CA-TABLES-09** Use `|...|` string templates to assemble text with embedded variables.
- **CA-TABLES-10** Use Booleans wisely — they break down when a third state is later needed.
- **CA-TABLES-11** Declare Booleans `TYPE abap_bool`.
- **CA-TABLES-12** Use `abap_true`/`abap_false`, not `'X'`/`' '`/`space`.
- **CA-TABLES-13** Use `xsdbool( )` to set a Boolean from a condition.
