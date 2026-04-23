#!/usr/bin/env python3
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import sys

from repo_policy import ROOT, scan_source_tree


def main() -> int:
    report = scan_source_tree(ROOT)
    has_failures = False
    if report["forbidden_files"]:
        has_failures = True
        print('Repo hygiene check failed. Remove these files before commit:', file=sys.stderr)
        for item in report["forbidden_files"]:
            print(f' - {item}', file=sys.stderr)
    if report["missing_doc_refs"]:
        has_failures = True
        print('Repo hygiene check failed. These markdown references point to missing docs:', file=sys.stderr)
        for item in report["missing_doc_refs"]:
            print(f" - {item['source']} -> {item['reference']}", file=sys.stderr)
    if report["legacy_root_leaks"]:
        has_failures = True
        print('Repo hygiene check failed. Legacy root shims leaked back into the active tree:', file=sys.stderr)
        for item in report["legacy_root_leaks"]:
            print(f' - {item}', file=sys.stderr)
    if has_failures:
        return 1
    print('Repo hygiene check passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
