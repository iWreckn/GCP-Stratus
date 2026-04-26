import hashlib
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List
from time import sleep
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from app.models import ReleaseNoteEvent
from app.config import logger

GCP_RSS_URL = "https://cloud.google.com/feeds/gcp-release-notes.xml"

def generate_event_hash(service: str, raw_text: str, published_date: str) -> str:
    """Generate a deterministic SHA-256 hash for an atomic event."""
    raw_string = f"{service}|{raw_text}|{published_date}".encode("utf-8")
    return hashlib.sha256(raw_string).hexdigest()

def fetch_release_notes(days_back: int = 10) -> List[ReleaseNoteEvent]:
    """
    Fetch recent GCP release notes via RSS, returning atomic event models.
    Includes basic retry logic.
    """
    logger.info(f"Fetching GCP release notes for the last {days_back} days...")
    
    response = None
    for attempt in range(1, 4):
        try:
            response = requests.get(GCP_RSS_URL, timeout=10)
            response.raise_for_status()
            break
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if attempt == 3:
                logger.error("Max retries reached. Aborting extraction.")
                raise
            sleep(2 ** attempt)

    feed = feedparser.parse(response.content)
    cutoff_date = datetime.now() - timedelta(days=days_back)
    events = []

    for entry in feed.entries:
        try:
            pub_date = datetime(*entry.published_parsed[:6])
        except (AttributeError, TypeError):
            pub_date = datetime.now()

        if pub_date < cutoff_date:
            continue
            
        published_week = pub_date.strftime("%Y-W%W")
        
        soup = BeautifulSoup(entry.description, "html.parser")
        title_tags = soup.find_all(class_="release-note-product-title")
        
        if title_tags:
            for h2 in title_tags:
                service = h2.get_text(strip=True)
                
                current_category = "Update"
                current_text_parts = []
                current_links = []
                
                for sibling in h2.find_next_siblings():
                    # Stop if we hit the next product header
                    if sibling.name == "h2" and "release-note-product-title" in sibling.get("class", []):
                        break
                    
                    # When we hit an H3 (e.g. Feature, Deprecated), we flush the previous event and start a new one
                    if sibling.name == "h3":
                        if current_text_parts:
                            raw_text = "\n\n".join(current_text_parts)
                            event_hash = generate_event_hash(service, raw_text, pub_date.isoformat())
                            events.append(ReleaseNoteEvent(
                                service=service,
                                published_date=pub_date.isoformat(),
                                raw_text=raw_text,
                                source_url=entry.link,
                                doc_links=",".join(current_links),
                                event_hash=event_hash,
                                category=current_category,
                                published_week=published_week
                            ))
                            current_text_parts = []
                            current_links = []
                        current_category = sibling.get_text(strip=True)
                    else:
                        text = sibling.get_text(separator=" ", strip=True)
                        if text:
                            current_text_parts.append(text)
                            
                        # Extract any documentation links hidden in the HTML
                        if hasattr(sibling, "find_all"):
                            for a in sibling.find_all("a", href=True):
                                href = a["href"]
                                if href.startswith("http") and href not in current_links:
                                    current_links.append(href)
                            
                if current_text_parts:
                    raw_text = "\n\n".join(current_text_parts)
                    event_hash = generate_event_hash(service, raw_text, pub_date.isoformat())
                    events.append(ReleaseNoteEvent(
                        service=service,
                        published_date=pub_date.isoformat(),
                        raw_text=raw_text,
                        source_url=entry.link,
                        doc_links=",".join(current_links),
                        event_hash=event_hash,
                        category=current_category,
                        published_week=published_week
                    ))
            continue

        # Fallback for generic entries
        service = "General"
        if hasattr(entry, 'tags') and entry.tags:
            ignore_tags = {"google cloud", "google cloud platform", "release notes", "general"}
            valid_tags = [tag.term for tag in entry.tags if tag.term.lower() not in ignore_tags]
            if valid_tags:
                service = valid_tags[0]

        raw_text = soup.get_text(separator="\n\n", strip=True)
        
        generic_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and href not in generic_links:
                generic_links.append(href)
                
        event_hash = generate_event_hash(service, raw_text, pub_date.isoformat())
        
        events.append(ReleaseNoteEvent(
            service=service,
            published_date=pub_date.isoformat(),
            raw_text=raw_text,
            source_url=entry.link,
            doc_links=",".join(generic_links),
            event_hash=event_hash,
            category="General",
            published_week=published_week
        ))

    logger.info(f"Successfully extracted {len(events)} atomic release note events.")
    return events