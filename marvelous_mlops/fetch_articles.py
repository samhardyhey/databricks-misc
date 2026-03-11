"""
Fetch Marvelous MLOps Medium articles metadata and summaries.

This script collects article metadata (titles, URLs, excerpts, dates) from the
Marvelous MLOps Medium publication for reference purposes.
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


def fetch_medium_rss_feed(publication_url: str) -> List[Dict]:
    """
    Fetch articles from Medium publication RSS feed.
    
    Args:
        publication_url: Medium publication URL
        
    Returns:
        List of article metadata dictionaries
    """
    # Medium RSS feeds use the format: https://medium.com/feed/{publication-slug}
    # Extract publication slug from URL
    publication_slug = publication_url.rstrip("/").split("/")[-1]
    rss_url = f"https://medium.com/feed/{publication_slug}"
    logger.info(f"Fetching RSS feed from: {rss_url}")
    
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
    
    articles = []
    for entry in feed.entries:
        article = {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "author": entry.get("author", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "tags": [tag.get("term", "") for tag in entry.get("tags", [])],
            "fetched_at": datetime.now().isoformat(),
        }
        articles.append(article)
        logger.info(f"Found article: {article['title']}")
    
    return articles


def fetch_article_preview(article_url: str, max_retries: int = 3) -> Dict:
    """
    Fetch publicly available preview/excerpt from article page.
    
    Args:
        article_url: URL of the article
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with article preview data
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; research bot)"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(article_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract meta description (publicly available preview)
            meta_desc = soup.find("meta", {"name": "description"})
            description = meta_desc.get("content", "") if meta_desc else ""
            
            # Extract reading time estimate
            reading_time_tag = soup.find("span", {"data-testid": "storyReadTime"})
            reading_time = reading_time_tag.text if reading_time_tag else ""
            
            return {
                "preview": description,
                "reading_time": reading_time,
            }
            
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed for {article_url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to fetch preview for {article_url}")
                return {"preview": "", "reading_time": ""}
    
    return {"preview": "", "reading_time": ""}


def save_articles_metadata(articles: List[Dict], output_dir: Path) -> None:
    """
    Save article metadata to JSON files.
    
    Args:
        articles: List of article metadata
        output_dir: Directory to save metadata files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full metadata list
    metadata_file = output_dir / "articles_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved metadata for {len(articles)} articles to {metadata_file}")
    
    # Save individual article references
    articles_dir = output_dir / "articles"
    articles_dir.mkdir(exist_ok=True)
    
    for idx, article in enumerate(articles, 1):
        # Create filename from title
        safe_title = "".join(
            c for c in article["title"] if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:100]
        safe_title = safe_title.replace(" ", "_")
        
        article_file = articles_dir / f"{idx:03d}_{safe_title}.json"
        with open(article_file, "w", encoding="utf-8") as f:
            json.dump(article, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(articles)} individual article references to {articles_dir}")
    
    # Create summary README
    readme_file = output_dir / "README.md"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write("# Marvelous MLOps Articles Reference\n\n")
        f.write(f"Fetched: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total articles: {len(articles)}\n\n")
        f.write("## Articles\n\n")
        
        for idx, article in enumerate(articles, 1):
            f.write(f"### {idx}. {article['title']}\n\n")
            f.write(f"- **Author**: {article['author']}\n")
            f.write(f"- **Published**: {article['published']}\n")
            f.write(f"- **URL**: {article['url']}\n")
            if article.get("tags"):
                f.write(f"- **Tags**: {', '.join(article['tags'])}\n")
            f.write(f"\n**Summary**: {article.get('summary', 'N/A')[:300]}...\n\n")
            f.write("---\n\n")
    
    logger.info(f"Created summary README at {readme_file}")


def main():
    """Main execution function."""
    publication_url = "https://medium.com/marvelous-mlops"
    output_dir = Path(__file__).parent
    
    logger.info("Starting Marvelous MLOps article metadata fetch")
    
    # Fetch articles from RSS feed
    articles = fetch_medium_rss_feed(publication_url)
    
    if not articles:
        logger.error("No articles found. Exiting.")
        return
    
    logger.info(f"Found {len(articles)} articles")
    
    # Optionally fetch additional preview data (with rate limiting)
    logger.info("Fetching article previews (rate limited)...")
    for idx, article in enumerate(articles):
        if idx > 0 and idx % 5 == 0:
            logger.info(f"Processed {idx}/{len(articles)} articles, pausing...")
            time.sleep(5)  # Rate limiting
        
        preview_data = fetch_article_preview(article["url"])
        article.update(preview_data)
        time.sleep(1)  # Be respectful with requests
    
    # Save metadata
    save_articles_metadata(articles, output_dir)
    
    logger.info("Article metadata fetch complete!")


if __name__ == "__main__":
    main()
