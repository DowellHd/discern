"""Run the Discern API locally in offline demo mode.

    python main.py                  # demo on http://localhost:8000
    python main.py --reset          # rebuild the demo database from scratch
    python main.py --real           # real services (Postgres, model, OCR) instead of the demo

Demo mode swaps every external service for a local mock: SQLite instead of Postgres, a mock
inference engine instead of the model + OCR backends, and a seeded document library. The real
code is untouched; `--real` (or DISCERN_OFFLINE_DEMO=false) switches straight back to it.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Run straight from a clone: no `pip install -e .` needed.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Discern API (offline demo by default).")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    parser.add_argument("--reset", action="store_true", help="delete and reseed the demo data")
    parser.add_argument("--real", action="store_true", help="use the real services, not the demo")
    args = parser.parse_args()

    # Settings are read at import time, so the environment must be set first.
    if not args.real:
        os.environ.setdefault("DISCERN_OFFLINE_DEMO", "true")

    import uvicorn

    from discern.config import settings

    if settings.offline_demo and args.reset:
        from discern.demo.bootstrap import reset_demo_data

        reset_demo_data()

    mode = "offline demo" if settings.offline_demo else "real services"
    print(f"Discern API starting in {mode} mode: http://{args.host}:{args.port}/docs")
    uvicorn.run("discern.api.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
