import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const fileExts = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);
const candidateExts = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"];
const ignoredDirs = new Set(["node_modules", ".next", "coverage", "test-results", "playwright-report"]);

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!ignoredDirs.has(entry.name)) walk(path.join(dir, entry.name), out);
    } else if (entry.isFile() && fileExts.has(path.extname(entry.name))) {
      out.push(path.join(dir, entry.name));
    }
  }
  return out;
}

function localBase(spec, fromDir) {
  if (spec.startsWith("@/")) return path.join(root, spec.slice(2));
  if (spec.startsWith(".")) return path.resolve(fromDir, spec);
  return null;
}

function existsLocalModule(base) {
  if (fs.existsSync(base)) return true;
  for (const ext of candidateExts) if (fs.existsSync(`${base}${ext}`)) return true;
  for (const ext of candidateExts) if (fs.existsSync(path.join(base, `index${ext}`))) return true;
  return false;
}

function stripLineComment(line) {
  let quote = "";
  let escaped = false;
  for (let i = 0; i < line.length - 1; i += 1) {
    const ch = line[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === quote) quote = "";
      continue;
    }
    if (ch === "\"" || ch === "'") {
      quote = ch;
      continue;
    }
    if (ch === "/" && line[i + 1] === "/") return line.slice(0, i);
  }
  return line;
}

function extractSpecs(source) {
  const specs = [];
  for (const raw of source.split(/\r?\n/)) {
    const line = stripLineComment(raw);
    const trimmed = line.trimStart();
    if (trimmed.startsWith("import ") || trimmed.startsWith("export ")) {
      const match = line.match(/(?:from\s*)?["']([^"']+)["']/);
      if (match) specs.push(match[1]);
    }
    for (const match of line.matchAll(/\bimport\s*\(\s*["']([^"']+)["']\s*\)/g)) {
      specs.push(match[1]);
    }
  }
  return specs;
}

const files = walk(root).sort();
const errors = [];
let imports = 0;
for (const file of files) {
  const source = fs.readFileSync(file, "utf8");
  for (const spec of extractSpecs(source)) {
    imports += 1;
    const base = localBase(spec, path.dirname(file));
    if (!base) continue;
    if (!existsLocalModule(base)) errors.push(`${path.relative(root, file)} -> ${spec}`);
  }
}

if (errors.length > 0) {
  fs.writeSync(2, `[imports:error] ${errors.length} unresolved local import${errors.length === 1 ? "" : "s"}\n`);
  for (const error of errors) fs.writeSync(2, ` - ${error}\n`);
  process.exit(1);
}

fs.writeSync(1, `[imports:ok] ${files.length} JS/TS files scanned; imports=${imports}\n`);
process.exit(0);
