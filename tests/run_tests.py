"""Quick runner — runs all tests in order and prints a clear pass/fail summary."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

tests = [
    ("Health endpoint", "tests/test_health.py"),
    ("Database layer", "tests/test_db.py"),
    ("Agent pipeline", "tests/test_agents.py"),
    ("Streaming API", "tests/test_stream.py"),
]

results = []
for label, path in tests:
    print(f"\n{'='*60}")
    print(f"  {label}  ({path})")
    print(f"{'='*60}")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-v", "-s", "--tb=short"],
        cwd=str(ROOT),
    )
    results.append((label, r.returncode == 0))

print(f"\n{'='*60}")
print("  SUMMARY")
print(f"{'='*60}")
for label, passed in results:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}]  {label}")

if not all(ok for _, ok in results):
    sys.exit(1)
