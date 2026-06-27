"""Thin client for Google News' public RSS search feed (https://news.google.com/rss).

No API key required. Returns structured XML (title/link/source/pubDate)
rather than scraped HTML, so it's less likely to break than parsing a
rendered search results page - but Google can still change the feed format
or rate-limit requests at any time.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

URL = "https://news.google.com/rss/search"
TIMEOUT_SECONDS = 10
MAX_RESULT_AGE_DAYS = 365 * 2


def search_news(query: str, max_results: int = 5) -> dict:
    """Run a Google News search and return parsed headlines from the last 2 years.

    On any error (network error, bad status code, unparseable XML), returns
    a dict of the form {"results": [], "error": "<message>"} instead of
    raising, so calling tools can surface this gracefully to the agent.

    Returns {"results": [{"title", "source", "published", "url"}, ...], "error": None}.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_RESULT_AGE_DAYS)).strftime("%Y-%m-%d")
    params = {"q": f"{query} after:{cutoff}", "hl": "en-US", "gl": "US", "ceid": "US:en"}
    try:
        response = requests.get(URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {"results": [], "error": f"Google News request failed: {exc}"}

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        return {"results": [], "error": f"Google News response was not valid XML: {exc}"}

    results = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title")
        if not title:
            continue
        source_el = item.find("source")
        results.append({
            "title": title,
            "source": source_el.text if source_el is not None else None,
            "published": item.findtext("pubDate"),
            "url": item.findtext("link"),
        })
        if len(results) >= max_results:
            break

    return {"results": results, "error": None}
