"""
Pinned download URLs for spaCy pipeline wheels (document intelligence).

Explosion does **not** publish these models on PyPI or as installable ``git+https``
trees: binaries live only as **release assets** on GitHub:

  https://github.com/explosion/spacy-models/releases

``python -m spacy download en_core_web_sm`` ultimately pulls the same style of URL.

Keep ``EN_CORE_WEB_SM_GH_TAG`` in sync with ``spacy`` in ``pyproject.toml`` (see each
release's ``requires_spacy`` / wheel ``METADATA``).
"""

from __future__ import annotations

# GitHub Release tag and wheel (canonical; works with `uv` / `pip` URL deps).
EN_CORE_WEB_SM_GH_TAG = "en_core_web_sm-3.8.0"
EN_CORE_WEB_SM_WHEEL_GITHUB = (
    "https://github.com/explosion/spacy-models/releases/download/"
    f"{EN_CORE_WEB_SM_GH_TAG}/{EN_CORE_WEB_SM_GH_TAG}-py3-none-any.whl"
)

# Optional mirror (Hugging Face). ``main`` tracks Explosion uploads but may not match
# every spaCy minor—inspect the wheel or HF README before swapping the primary URL.
EN_CORE_WEB_SM_WHEEL_HUGGINGFACE_MAIN = (
    "https://huggingface.co/spacy/en_core_web_sm/"
    "resolve/main/en_core_web_sm-any-py3-none-any.whl"
)
