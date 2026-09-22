#!/usr/bin/env python3
"""Run all tests and print results."""
import pytest
import sys

result = pytest.main([
    "tests/",
    "--tb=short",
    "-q",
    "-v",
])

print(f"\n{'='*60}")
print(f"Tests completed with exit code: {result}")
print(f"{'='*60}")

sys.exit(result)
