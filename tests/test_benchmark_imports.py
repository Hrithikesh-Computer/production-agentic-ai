from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks" / "response-delivery"


def test_response_delivery_benchmark_modules_import() -> None:
    script = (
        "import sys; "
        f"sys.path.insert(0, {str(BENCHMARKS)!r}); "
        "import benchmark; "
        "import browser_benchmark"
    )
    subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True)