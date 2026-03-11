# Substack Posts Collection

**Status:** Not yet configured

## Setup

1. Edit `fetch_substack.py` and update the `publication_url` variable
2. Run: `python fetch_substack.py`
3. Check this file for fetched content summary

## Potential Sources

- **Newsletter double** (Eugene Yan): https://www.evidentlyai.com/newsletter
- **MLOps Community**: Various newsletters
- **Individual practitioners**: Chip Huyen, Shreya Shankar, etc.

## Content Structure

Once fetched, content will be organized as:
- `metadata.json` - All posts metadata
- `content/posts/` - Individual post JSON files

Each post JSON contains:
- Title
- URL
- Author
- Publication date
- Summary/excerpt
- Tags
- Fetch timestamp
