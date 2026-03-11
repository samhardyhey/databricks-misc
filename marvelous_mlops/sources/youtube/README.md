# YouTube Transcripts Collection

**Status:** Not yet configured

## Setup

1. Install dependencies: `pip install youtube-transcript-api`
2. Edit `fetch_youtube.py` and add video URLs to the `video_urls` list
3. Run: `python fetch_youtube.py`
4. Check this file for fetched content summary

## Potential Sources

### Channels
- **Databricks** - Official channel with Data+AI Summit talks
- **MLOps Community** - Community presentations
- **Applied ML** - Practical tutorials

### Playlists
- Databricks MLOps course
- Conference talks (MLOps World, apply(conf), etc.)
- Tutorial series

### Individual Videos
- Key presentations on:
  - Model deployment patterns
  - Feature stores
  - ML monitoring
  - CI/CD for ML
  - Model serving architectures

## Content Structure

Once fetched, content will be organized as:
- `metadata.json` - All videos metadata
- `content/transcripts/` - Individual transcript JSON files

Each transcript JSON contains:
- Video ID
- URL
- Full transcript text
- Transcript segments (with timestamps)
- Language
- Fetch timestamp
- Error info (if transcript unavailable)

## Transcript Availability

Note: Not all videos have transcripts. The fetcher will:
- Try to fetch auto-generated or manual transcripts
- Log warnings for videos without transcripts
- Continue processing remaining videos
- Save error information in metadata
