# MLOps Reference Content Aggregator

Multi-source content fetcher for MLOps best practices, patterns, and tutorials.

## Overview

This repository aggregates MLOps-related content from multiple sources:
- **Medium** - Articles from Marvelous MLOps and other publications
- **Substack** - Newsletter posts from MLOps practitioners
- **YouTube** - Video transcripts from MLOps channels and presentations

## Directory Structure

```
marvelous_mlops/
├── fetch_medium.py           # Fetch Medium articles
├── fetch_substack.py         # Fetch Substack posts
├── fetch_youtube.py          # Fetch YouTube transcripts
├── requirements.txt          # Python dependencies
├── README.md                 # This file
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

```bash
pip install -r requirements.txt
```

## Usage

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

1. **Configure Substack sources** - Identify relevant MLOps newsletters
2. **Add YouTube channels** - Databricks talks, conference presentations, tutorials
3. **Automate updates** - Schedule periodic fetches (e.g., weekly cron job)
4. **Build search index** - Add semantic search capabilities (e.g., embeddings + vector DB)
5. **Create web interface** - Simple UI for browsing aggregated content
6. **Add RSS aggregator** - Monitor multiple sources automatically

## License

Content belongs to original creators. This tool aggregates publicly available metadata for personal reference purposes only.
