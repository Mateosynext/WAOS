import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const exts = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"];
const scanExts = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);
const ignoredDirs = new Set(["node_modules", ".next", "coverage", "test-results", "playwright-report"]);
const importPattern = /^\s*(?:import|export)\s+(?:[^'"]*?\s+from\s+)?["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/gm;

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!ignoredDirs.has(entry.name)) walk(path.join(dir, entry.name), files);
      continue;
    }
    if (entry.isFile() && scanExts.has(path.extname(entry.name))) {
      files.push(path.join(dir, entry.name));
    }
  }
  return files;
}

function candidatesFor(spec, fromDir) {
  let base;
  if (spec.startsWith("@/")) {
    base = path.join(root, spec.slice(2));
  } else if (spec.startsWith(".")) {
    base = path.resolve(fromDir, spec);
  } else {
    return [];
  }

  const candidates = [base];
  for (const ext of exts) candidates.push(`${base}${ext}`);
  for (const ext of exts) candidates.push(path.join(base, `index${ext}`));
  return candidates;
}

const errors = [];
const files = walk(root);
for (const file of files) {
  const source = fs.readFileSync(file, "utf8");
  importPattern.lastIndex = 0;
  for (const match of source.matchAll(importPattern)) {
    const spec = match[1] || match[2];
    const candidates = candidatesFor(spec, path.dirname(file));
    if (!candidates.length) continue;
    if (!candidates.some((candidate) => fs.existsSync(candidate))) {
      errors.push(`${path.relative(root, file)} -> ${spec}`);
    }
  }
}

if (errors.length) {
  console.error(`[imports:error] ${errors.length} unresolved local import${errors.length === 1 ? "" : "s"}`);
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}

console.log(`[imports:ok] ${files.length} JS/TS files scanned`);
