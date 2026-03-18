"""
Document intelligence smoke test (local).

Runs the full local pipeline:
1) generate prescription PDFs + JSON labels
2) OCR extraction
3) field extraction (OCR + proxy NER)
4) start the Streamlit annotator app in headless mode briefly (ensures it can import/run)

This is a lightweight orchestration wrapper intended for quick verification after changes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

from use_cases.document_intelligence.config import get_config


def _run_python(script_path: Path, env: dict[str, str], timeout_s: int | None = None) -> None:
    """Run a python script and fail fast on non-zero exit."""
    cmd = [sys.executable, str(script_path)]
    logger.info("smoke: running {}", " ".join(cmd))
    subprocess.run(cmd, cwd=str(Path(__file__).resolve().parents[2]), env=env, check=True, timeout=timeout_s)


def _start_streamlit_briefly(env: dict[str, str], app_path: Path, wait_s: int = 8) -> None:
    """
    Start Streamlit and terminate after a short wait.

    We don't try to validate UI interactions; the goal is to verify the app can start.
    """
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--server.port=8502",
        "--browser.gatherUsageStats=false",
        "--logger.level=error",
    ]

    logger.info("smoke: starting streamlit briefly (headless)")
    proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        time.sleep(wait_s)
        if proc.poll() is not None:
            # Process already exited (likely import error).
            out, _ = proc.communicate(timeout=5)
            raise RuntimeError(f"Streamlit exited early. Output:\n{out}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def main() -> dict:
    # Speed up smoke by default (override externally if desired).
    os.environ.setdefault("DOCINT_NUM_PDFS", "3")
    os.environ.setdefault("DOCINT_SEED", "42")
    os.environ["DOCINT_DATA_SOURCE"] = "local"

    cfg = get_config()
    base_dir = Path(cfg["base_dir"])

    # Streamlit dependency check (fail with actionable message).
    try:
        import streamlit  # type: ignore[import-not-found]  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "streamlit is not installed. Run: make document-intelligence-install"
        ) from e

    jobs_dir = Path(__file__).resolve().parent / "jobs"

    _run_python(jobs_dir / "1_generate_data.py", env=os.environ.copy())
    _run_python(jobs_dir / "2_ocr_extraction.py", env=os.environ.copy())
    _run_python(jobs_dir / "3_field_extraction.py", env=os.environ.copy())

    fields_dir = base_dir / "predictions" / "fields"
    if not fields_dir.exists():
        raise RuntimeError(f"Smoke failed: expected fields output at {fields_dir} but it does not exist.")

    # Start the annotator app briefly (headless) so import/runtime errors are caught.
    app_path = Path(__file__).resolve().parent / "annotator" / "app.py"
    _start_streamlit_briefly(env=os.environ.copy(), app_path=app_path)

    logger.success("document-intelligence smoke done")
    return {"base_dir": str(base_dir), "fields_dir": str(fields_dir)}


if __name__ == "__main__":
    result = main()
    logger.info("document-intelligence smoke result: {}", result)

