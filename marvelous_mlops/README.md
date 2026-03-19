# MLOps reference content (Databricks policy development)

This folder supports **policy development** for the parent EBOS/Databricks repo: we **scrape or pull public, RSS/feed-level material** from curated sources—primarily **[Marvelous MLOps on Medium](https://medium.com/marvelous-mlops)**—so maintainers can **summarize and extract practical tips and best practices** for Unity Catalog, Asset Bundles, Model Serving, MLflow, monitoring, and CI/CD. Outputs feed internal docs, Makefile/workflows, and Cursor/project rules; they are **not** a redistribution channel for full article text.

**Workflow:** fetch fresh metadata → run **`extract_practice_digest.py`** (or `make marvelous-mlops-practice-digest` from repo root) → review `insights/` markdown and promote stable guidance into `docs/` or `.cursor/rules/` as needed.

---

## MLOps reference content aggregator

Multi-source content fetcher for MLOps best practices, patterns, and tutorials.

## Overview

This tool aggregates MLOps-related content from multiple sources:
- **Medium** - Articles from Marvelous MLOps and other publications
- **Substack** - Newsletter posts from MLOps practitioners
- **YouTube** - Video transcripts from MLOps channels and presentations

## Directory Structure

```
marvelous_mlops/
├── extract_practice_digest.py # Markdown digest from fetched JSON (policy notes)
├── fetch_medium.py           # Fetch Medium articles
├── fetch_substack.py         # Fetch Substack posts
├── fetch_youtube.py          # Fetch YouTube transcripts
├── README.md                 # This file
├── insights/                 # Generated digests (git-track optional)
└── sources/                  # Content organized by source
    ├── medium/
    │   ├── metadata.json     # All articles metadata
    │   ├── README.md         # Medium-specific summary
    │   └── content/
    │       └── articles/     # Individual article JSON files
    ├── substack/
    │   ├── metadata.json     # All posts metadata
    │   └── content/
    │       └── posts/        # Individual post JSON files
    └── youtube/
        ├── metadata.json     # All videos metadata
        └── content/
            └── transcripts/  # Individual transcript JSON files
```

## Installation

Dependencies are the **`marvelous_mlops`** optional group in the repo root **`pyproject.toml`** (same pattern as `reco`, `document_intelligence`, etc.).

From repo root:

```bash
make marvelous-mlops-venv
```

Or with uv: `uv pip install -e ".[marvelous_mlops]"`
Or: `pip install -e ".[marvelous_mlops]"`

Uses the **shared repo `.venv`** (not a separate virtualenv under this folder).

## Usage

### Build Databricks practice digest (from already-fetched JSON)

After fetching, generate a single markdown file of **extracted bullets and plain-text summaries** (best for scanning before updating repo policy):

```bash
python extract_practice_digest.py
```

From repo root: `make marvelous-mlops-practice-digest` (requires `make marvelous-mlops-venv` first).

### Fetch Medium Articles

```bash
python fetch_medium.py
```

Currently configured for **Marvelous MLOps** publication. To fetch from different Medium publications, edit `fetch_medium.py` and update the `publication_url` variable.

### Fetch Substack Posts

```bash
python fetch_substack.py
```

**TODO:** Update `publication_url` in `fetch_substack.py` with your target Substack newsletter URL.

### Fetch YouTube Transcripts

```bash
python fetch_youtube.py
```

**TODO:** Add video URLs to the `video_urls` list in `fetch_youtube.py`.

## Content Sources

### Medium (Active) ✓

**Publication:** Marvelous MLOps
**URL:** https://medium.com/marvelous-mlops
**Last Fetched:** 2026-03-11
**Articles:** 10

**Key Topics:**
- Databricks MLOps course series (Lectures 3-10)
- MLflow and model deployment
- Databricks Asset Bundles (DABs)
- CI/CD for ML
- Model monitoring and drift detection
- LLM patterns and anti-patterns
- Python environment management (UV)

See [sources/medium/README.md](sources/medium/README.md) for detailed article listing.

### Substack (Template)

**Status:** Template created, needs configuration

Configure your target Substack publication(s) in `fetch_substack.py`.

Potential sources:
- Newsletter double (Eugene Yan)
- MLOps Community newsletters
- Individual practitioner newsletters

### YouTube (Template)

**Status:** Template created, needs video URLs

Add relevant MLOps channel videos or playlists to `fetch_youtube.py`.

Potential sources:
- Databricks official channel
- MLOps Community talks
- Conference presentations (Data+AI Summit, etc.)
- Tutorial channels

## Rate Limiting & Ethics

All fetchers implement:
- Rate limiting (1-5 second delays between requests)
- Respectful crawling (User-Agent headers, exponential backoff)
- Public content only (no paywall bypass)
- Copyright compliance (metadata and excerpts only)

## Output Format

Each source outputs:
1. **metadata.json** - Complete list of all items with full metadata
2. **content/** - Individual JSON files for each item
3. Each JSON file contains:
   - Title/description
   - URL
   - Author/channel
   - Publication date
   - Summary/excerpt/transcript
   - Tags/categories
   - Fetch timestamp

## Use Cases

This aggregated content is useful for:
- Building MLOps knowledge bases
- Training documentation retrieval systems
- Tracking MLOps best practices evolution
- Creating curated reading lists
- RAG (Retrieval-Augmented Generation) applications
- Research and analysis

## Implementation Notes

### Medium Fetcher
- Uses RSS feed: `https://medium.com/feed/{publication-slug}`
- Fetches article metadata + publicly available previews
- Rate limited to respect Medium's terms

### Substack Fetcher
- Uses RSS feed: `{publication-url}/feed`
- Similar structure to Medium fetcher
- Extracts post excerpts and metadata

### YouTube Fetcher
- Uses `youtube-transcript-api` library
- Extracts available transcripts (auto-generated or manual)
- Handles various YouTube URL formats
- Gracefully handles videos without transcripts

## Next Steps

1. **Promote digest into repo policy** - Fold recurring themes from `insights/` into `docs/` and `.cursor/rules/` where they clarify Databricks bundles, UC, or MLflow usage.
2. **Configure Substack sources** - Identify relevant MLOps newsletters
3. **Add YouTube channels** - Databricks talks, conference presentations, tutorials
4. **Automate updates** - Schedule periodic fetches (e.g., weekly cron job)
5. **Build search index** - Optional embeddings + vector DB for RAG over digests
6. **Add RSS aggregator** - Monitor multiple sources automatically

## License

Content belongs to original creators. This tool aggregates publicly available metadata for personal reference purposes only.
