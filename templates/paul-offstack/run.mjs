// Off-stack ABAP Unit runner (transpile phase). Write Path B companion; no live
// SAP system. Reusable template — nothing in this file is repo-specific; all
// per-repo variation lives in abap_transpile.json (input folders, exclude_filter
// naming the shimmed class, and the "syntax_version" pin) plus the shim/ and
// ddic/ folders.
//
// Why this exists rather than the plain `abap_transpile` CLI: the CLI hard-codes
// its parse dialect to Release.Newest (a permissive sentinel) and exposes no
// syntax-version pin. To make the off-stack parse read the SAME dialect as the
// on-stack ATC/abaplint gate, this runner constructs the abaplint Registry with
// Config.getDefault(Version[<syntax_version>]) — the version read from
// abap_transpile.json so this file stays generic across repos. Everything else
// mirrors the CLI's build:
//   - src/ (minus the excluded real adapter) + shim/ + ddic/ as files
//   - open-abap-core src/ (minus *.clas.testclasses.abap) as dependencies
//   - transpile, write the object .mjs + the generated AUnit index.mjs
// The generated build/index.mjs is then executed by `node build/index.mjs`
// (see package.json "test"), which is what actually runs the tests.

import { Registry, Config, MemoryFile, Version } from "@abaplint/core";
import { Transpiler } from "@abaplint/transpiler";
import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { glob } from "glob";

const CFG = JSON.parse(fs.readFileSync("abap_transpile.json", "utf8"));
const OUT = CFG.output_folder;

// Dialect pin, read from config so this runner is repo-agnostic. Set
// "syntax_version" in abap_transpile.json to match the repo-root abaplint.json
// (e.g. "v816" for SAP_BASIS 816 / S/4HANA 2025).
const versionKey = CFG.syntax_version ?? "Newest";
const version = Version[versionKey];
if (!version) {
  throw new Error(
    `Unknown syntax_version '${versionKey}' in abap_transpile.json — ` +
    `use an @abaplint/core Version key such as "v816".`
  );
}

// open-abap-core is the standard-library dependency (MIT, from the open-abap
// org): it supplies cl_abap_unit_assert, if_aunit_constants, the AUnit runner,
// cx_root/cx_static_check, bapiret2, land1, etc. Pinned to a commit for
// reproducibility. Not vendored into the repo (git-ignored); cloned on demand
// so a fresh checkout and CI both resolve the same tree.
const LIB_REPO = "https://github.com/open-abap/open-abap-core";
const LIB_PIN = "c0e8bb8480a17bbb066579d264469bdb9d571589";
const LIB_DIR = "vendor-open-abap-core";

function ensureLib() {
  if (fs.existsSync(LIB_DIR + "/src")) return;
  console.log(`Cloning ${LIB_REPO} @ ${LIB_PIN.slice(0, 10)} ...`);
  execSync(`git clone --quiet ${LIB_REPO} ${LIB_DIR}`, { stdio: "inherit" });
  execSync(`git -C ${LIB_DIR} checkout --quiet ${LIB_PIN}`, { stdio: "inherit" });
}
ensureLib();

function readGlobFiles(folders, excludeRegexes, { skipTestClasses } = {}) {
  const out = [];
  for (const folder of folders) {
    for (const filename of glob.sync(folder + "/**", { nosort: true, nodir: true })) {
      if (skipTestClasses && filename.endsWith(".clas.testclasses.abap")) continue;
      if (excludeRegexes.some((r) => r.test(filename))) continue;
      out.push({ filename: path.basename(filename), contents: fs.readFileSync(filename, "utf8") });
    }
  }
  return out;
}

// ---- main input: src (minus excluded adapter) + shim + ddic --------------
const excludeRegexes = (CFG.exclude_filter ?? []).map((p) => new RegExp(p, "i"));
const inputFiles = readGlobFiles(CFG.input_folder, excludeRegexes);

// ---- dependency lib: open-abap-core --------------------------------------
const libFiles = [];
for (const lib of CFG.libs ?? []) {
  const dir = process.cwd() + lib.folder;
  const patterns = Array.isArray(lib.files) ? lib.files : [lib.files ?? "/src/**"];
  const libExclude = (lib.exclude_filter ?? []).map((p) => new RegExp(p, "i"));
  for (const pattern of patterns) {
    for (const filename of glob.sync(dir + pattern, { nosort: true, nodir: true })) {
      if (filename.endsWith(".clas.testclasses.abap")) continue;
      if (libExclude.some((r) => r.test(filename))) continue;
      libFiles.push({ filename: path.basename(filename), contents: fs.readFileSync(filename, "utf8") });
    }
  }
}

// ---- registry pinned to the configured dialect ---------------------------
const config = Config.getDefault(version);
const reg = new Registry(config);
for (const f of inputFiles) reg.addFile(new MemoryFile(f.filename, f.contents));
for (const l of libFiles) reg.addDependency(new MemoryFile(l.filename, l.contents));
reg.parse();

console.log(`Dialect pinned: ${config.getSyntaxSetttings().version}`);
console.log(`${inputFiles.length} source files (real adapter excluded), ${libFiles.length} open-abap-core dependency files`);

const transpiler = new Transpiler(CFG.options);
const output = await transpiler.run(reg);

// ---- write output, mirroring @abaplint/transpiler-cli --------------------
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });
for (const o of output.objects) {
  let contents = o.chunk.getCode();
  if (o.object.type.toUpperCase() === "PROG") {
    contents = `if (!globalThis.abap) await import("./_init.mjs");\n` + contents;
  }
  fs.writeFileSync(path.join(OUT, o.filename), contents);
}
fs.writeFileSync(path.join(OUT, "index.mjs"), output.unitTestScript);
fs.writeFileSync(path.join(OUT, "_unit_open.mjs"), output.unitTestScriptOpen);
fs.writeFileSync(path.join(OUT, "init.mjs"), output.initializationScript);
fs.writeFileSync(path.join(OUT, "_init.mjs"), output.initializationScript2);
fs.writeFileSync(path.join(OUT, "_top.mjs"), `import runtime from "@abaplint/runtime";\nglobalThis.abap = new runtime.ABAP();`);

console.log(`${output.objects.length} objects written to ${OUT}/`);
