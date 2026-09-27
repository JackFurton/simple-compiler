#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path

tests = [
    "test_lexer.py",
    "test_parser.py",
    "test_compiler.py",
    "test_vm.py",
    "test_collections.py",
    "test_optimizer.py",
    "test_serializer.py",
    "test_stdlib.py",
    "test_closures.py",
    "test_classes.py",
    "test_debugger.py",
    "test_basic.py",
]

test_dir = Path(__file__).parent

print("=" * 60)
print("Running Complete Compiler & VM Test Suite")
print("=" * 60)

all_passed = True
for test_file in tests:
    test_path = test_dir / test_file
    print(f"\n[RUN] Running {test_file}...")
    res = subprocess.run([sys.executable, str(test_path)])
    if res.returncode != 0:
        print(f"[FAIL] {test_file} FAILED")
        all_passed = False
    else:
        print(f"[PASS] {test_file} PASSED")

print("\n" + "=" * 60)
if all_passed:
    print("ALL TEST SUITES PASSED SUCCESSFULLY!")
    sys.exit(0)
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
