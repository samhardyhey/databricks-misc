"""
Fetch YouTube video transcripts and metadata.

This script collects video metadata and transcripts from YouTube
channels or playlists for reference purposes.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    logger.warning("youtube-transcript-api not installed. Install with: pip install youtube-transcript-api")


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video ID or None if invalid
    """
    # Handle different YouTube URL formats
    if "youtube.com/watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/embed/" in url:
        return url.split("embed/")[1].split("?")[0]
    return None


def fetch_transcript(video_id: str, languages: List[str] = None) -> Dict:
    """
    Fetch transcript for a YouTube video.
    
    Args:
        video_id: YouTube video ID
        languages: Preferred language codes (default: ['en'])
        
    Returns:
        Dictionary with transcript data
    """
    if not YOUTUBE_AVAILABLE:
        logger.error("youtube-transcript-api not installed")
        return {"transcript": "", "error": "youtube-transcript-api not installed"}
    
    if languages is None:
        languages = ['en']
    
    try:
        # Get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        
        # Format transcript
        full_transcript = " ".join([item['text'] for item in transcript_list])
        
        return {
            "transcript": full_transcript,
            "transcript_segments": transcript_list,
            "language": languages[0],
            "fetched_at": datetime.now().isoformat(),
            "error": None,
        }
        
    except NoTranscriptFound:
        logger.warning(f"No transcript found for video {video_id}")
        return {"transcript": "", "error": "No transcript found"}
    except TranscriptsDisabled:
        logger.warning(f"Transcripts disabled for video {video_id}")
        return {"transcript": "", "error": "Transcripts disabled"}
    except VideoUnavailable:
        logger.warning(f"Video {video_id} unavailable")
        return {"transcript": "", "error": "Video unavailable"}
    except Exception as e:
        logger.error(f"Error fetching transcript for {video_id}: {e}")
        return {"transcript": "", "error": str(e)}


def fetch_videos_from_list(video_urls: List[str]) -> List[Dict]:
    """
    Fetch transcripts for a list of video URLs.
    
    Args:
        video_urls: List of YouTube video URLs
        
    Returns:
        List of video metadata with transcripts
    """
    videos = []
    
    for url in video_urls:
        video_id = extract_video_id(url)
        if not video_id:
            logger.warning(f"Could not extract video ID from: {url}")
            continue
        
        logger.info(f"Fetching transcript for video: {video_id}")
        transcript_data = fetch_transcript(video_id)
        
        video = {
            "video_id": video_id,
            "url": url,
            **transcript_data,
        }
        videos.append(video)
        
        # Rate limiting
        time.sleep(1)
    
    return videos


def save_transcripts_metadata(videos: List[Dict], output_dir: Path) -> None:
    """
    Save video transcripts and metadata to JSON files.
    
    Args:
        videos: List of video metadata with transcripts
        output_dir: Directory to save metadata files (sources/youtube/)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full metadata list
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved metadata for {len(videos)} videos to {metadata_file}")
    
    # Save individual transcripts
    content_dir = output_dir / "content" / "transcripts"
    content_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, video in enumerate(videos, 1):
        video_file = content_dir / f"{idx:03d}_{video['video_id']}.json"
        with open(video_file, "w", encoding="utf-8") as f:
            json.dump(video, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(videos)} individual transcripts to {content_dir}")


def main():
    """Main execution function."""
    # TODO: Replace with actual video URLs from MLOps channels/playlists
    video_urls = [
        # Example: "https://www.youtube.com/watch?v=VIDEO_ID",
    ]
    
    if not video_urls:
        logger.warning("No video URLs provided. Add URLs to the video_urls list in main().")
        logger.info("Example video URL formats:")
        logger.info("  - https://www.youtube.com/watch?v=VIDEO_ID")
        logger.info("  - https://youtu.be/VIDEO_ID")
        return
    
    output_dir = Path(__file__).parent / "sources" / "youtube"
    
    logger.info(f"Starting YouTube transcript fetch for {len(video_urls)} videos")
    
    # Fetch transcripts
    videos = fetch_videos_from_list(video_urls)
    
    if not videos:
        logger.error("No videos processed. Exiting.")
        return
    
    logger.info(f"Processed {len(videos)} videos")
    
    # Save metadata
    save_transcripts_metadata(videos, output_dir)
    
    logger.info("Transcript fetch complete!")


if __name__ == "__main__":
    main()
