"""
Check for ``en_core_web_sm`` and optionally ``pip install`` the pinned GitHub wheel.

Used by ``spacy_ner_pipeline.get_nlp()`` before ``spacy.load``. Can also run as a script
(see ``main()``) from Make or CI.

Environment:

- ``DOCINT_AUTO_INSTALL_SPACY_MODEL`` — default ``1`` / ``true``: run ``pip install <wheel>``
  when the package is missing. Set ``0`` / ``false`` / ``no`` to only check (use blank:en fallback).
- ``DOCINT_EN_CORE_WEB_SM_WHEEL_URL`` — override wheel URL (default: ``model_dep_urls`` GitHub URL).

Read-only / managed clusters (e.g. Databricks) should bake the wheel into the environment or image;
auto-install often fails without write access to site-packages.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from loguru import logger

from use_cases.document_intelligence.model_dep_urls import EN_CORE_WEB_SM_WHEEL_GITHUB


def en_core_web_sm_importable() -> bool:
    """True if the ``en_core_web_sm`` package is on the path (wheel installed)."""
    try:
        import en_core_web_sm  # noqa: F401
    except ImportError:
        return False
    return True


def en_core_web_sm_loadable() -> bool:
    """True if ``spacy.load('en_core_web_sm')`` succeeds (valid version vs spaCy)."""
    try:
        import spacy

        spacy.load("en_core_web_sm")
    except (OSError, ImportError):
        return False
    return True


def _auto_install_enabled() -> bool:
    raw = os.environ.get("DOCINT_AUTO_INSTALL_SPACY_MODEL", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def ensure_en_core_web_sm(
    *,
    install: bool | None = None,
    wheel_url: str | None = None,
) -> bool:
    """
    Ensure ``en_core_web_sm`` is usable.

    If missing and ``install`` is true, runs
    ``sys.executable -m pip install <wheel>`` (default URL from ``model_dep_urls``).

    Returns True if ``spacy.load('en_core_web_sm')`` works after any install attempt.
    """
    if en_core_web_sm_loadable():
        return True

    if en_core_web_sm_importable():
        logger.warning(
            "en_core_web_sm is installed but spacy.load('en_core_web_sm') failed — "
            "check spaCy vs wheel compatibility (see model_dep_urls / pyproject.toml)."
        )

    do_install = _auto_install_enabled() if install is None else install
    if not do_install:
        logger.warning(
            "en_core_web_sm not loadable; auto-install disabled "
            "(set DOCINT_AUTO_INSTALL_SPACY_MODEL=1 to enable)."
        )
        return False

    url = (
        wheel_url or os.environ.get("DOCINT_EN_CORE_WEB_SM_WHEEL_URL") or ""
    ).strip() or EN_CORE_WEB_SM_WHEEL_GITHUB
    logger.info("Installing en_core_web_sm wheel: {}", url)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", url],
            check=True,
            timeout=600,
        )
    except subprocess.CalledProcessError as e:
        logger.error("pip install en_core_web_sm failed: {}", e)
        return False
    except subprocess.TimeoutExpired:
        logger.error("pip install en_core_web_sm timed out")
        return False

    if not en_core_web_sm_loadable():
        logger.error(
            "en_core_web_sm still not loadable after pip install "
            "(spaCy vs wheel version mismatch? check spacy and wheel tags)."
        )
        return False
    logger.info("en_core_web_sm is loadable.")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check / install en_core_web_sm (spaCy English pipeline)."
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Do not pip install; exit 1 if the model is not loadable.",
    )
    args = parser.parse_args(argv)
    if args.check_only:
        ok = en_core_web_sm_loadable()
        if not ok:
            logger.warning(
                "en_core_web_sm is not loadable. Install with: {} -m pip install {}",
                sys.executable,
                EN_CORE_WEB_SM_WHEEL_GITHUB,
            )
        return 0 if ok else 1
    ok = ensure_en_core_web_sm(install=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
