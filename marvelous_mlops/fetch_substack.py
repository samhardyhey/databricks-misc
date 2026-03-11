"""
Fetch Substack newsletter posts metadata and content.

This script collects post metadata (titles, URLs, excerpts, dates) from
Substack publications for reference purposes.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import feedparser
import requests
from bs4 import BeautifulSoup
from loguru import logger


def fetch_substack_rss_feed(publication_url: str) -> List[Dict]:
    """
    Fetch posts from Substack publication RSS feed.
    
    Args:
        publication_url: Substack publication URL (e.g., https://example.substack.com)
        
    Returns:
        List of post metadata dictionaries
    """
    rss_url = f"{publication_url}/feed"
    logger.info(f"Fetching RSS feed from: {rss_url}")
    
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
    
    posts = []
    for entry in feed.entries:
        post = {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "author": entry.get("author", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "tags": [tag.get("term", "") for tag in entry.get("tags", [])],
            "fetched_at": datetime.now().isoformat(),
        }
        posts.append(post)
        logger.info(f"Found post: {post['title']}")
    
    return posts


def fetch_post_preview(post_url: str, max_retries: int = 3) -> Dict:
    """
    Fetch publicly available preview/excerpt from post page.
    
    Args:
        post_url: URL of the post
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with post preview data
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; research bot)"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(post_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract meta description
            meta_desc = soup.find("meta", {"property": "og:description"})
            description = meta_desc.get("content", "") if meta_desc else ""
            
            # Extract reading time if available
            reading_time = ""
            time_tag = soup.find("span", class_="reading-time")
            if time_tag:
                reading_time = time_tag.text.strip()
            
            return {
                "preview": description,
                "reading_time": reading_time,
            }
            
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed for {post_url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"Failed to fetch preview for {post_url}")
                return {"preview": "", "reading_time": ""}
    
    return {"preview": "", "reading_time": ""}


def save_posts_metadata(posts: List[Dict], output_dir: Path) -> None:
    """
    Save post metadata to JSON files.
    
    Args:
        posts: List of post metadata
        output_dir: Directory to save metadata files (sources/substack/)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full metadata list
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved metadata for {len(posts)} posts to {metadata_file}")
    
    # Save individual post references
    content_dir = output_dir / "content" / "posts"
    content_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, post in enumerate(posts, 1):
        # Create filename from title
        safe_title = "".join(
            c for c in post["title"] if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:100]
        safe_title = safe_title.replace(" ", "_")
        
        post_file = content_dir / f"{idx:03d}_{safe_title}.json"
        with open(post_file, "w", encoding="utf-8") as f:
            json.dump(post, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(posts)} individual post references to {content_dir}")


def main():
    """Main execution function."""
    # TODO: Replace with actual Substack publication URL
    publication_url = "https://example.substack.com"
    output_dir = Path(__file__).parent / "sources" / "substack"
    
    logger.info(f"Starting Substack post metadata fetch for: {publication_url}")
    
    # Fetch posts from RSS feed
    posts = fetch_substack_rss_feed(publication_url)
    
    if not posts:
        logger.error("No posts found. Exiting.")
        return
    
    logger.info(f"Found {len(posts)} posts")
    
    # Optionally fetch additional preview data (with rate limiting)
    logger.info("Fetching post previews (rate limited)...")
    for idx, post in enumerate(posts):
        if idx > 0 and idx % 5 == 0:
            logger.info(f"Processed {idx}/{len(posts)} posts, pausing...")
            time.sleep(5)
        
        preview_data = fetch_post_preview(post["url"])
        post.update(preview_data)
        time.sleep(1)
    
    # Save metadata
    save_posts_metadata(posts, output_dir)
    
    logger.info("Post metadata fetch complete!")


if __name__ == "__main__":
    main()
