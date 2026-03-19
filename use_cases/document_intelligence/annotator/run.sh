#!/usr/bin/env bash
# Run from repo root for full-repo file watching + .streamlit/config.toml:
#   streamlit run use_cases/document_intelligence/annotator/app.py
# This script is for running inside annotator/ only (watches this directory tree).

set -euo pipefail
cd "$(dirname "$0")"
exec streamlit run app.py --server.runOnSave true --server.fileWatcherType auto
