import os
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import streamlit as st

def get_secret(key):
    try:
        return os.getenv(key) or st.secrets[key]
    except Exception:
        return os.getenv(key)

# Load environment
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NotionClinicalServer")

# MCP Server
mcp = FastMCP("Notion Clinical Server")


# ─────────────────────────────────────────────────────────────
# 1. CLIENT INITIALIZATION
# ─────────────────────────────────────────────────────────────
def _get_notion_client():
    try:
        from notion_client import Client

        api_key = get_secret("NOTION_API_KEY")
        if not api_key:
            logger.error("NOTION_API_KEY missing")
            return None

        return Client(auth=api_key)

    except Exception as e:
        logger.error(f"Client init failed: {str(e)}")
        return None


# ─────────────────────────────────────────────────────────────
# 2. SAFE TITLE EXTRACTION (ROBUST)
# ─────────────────────────────────────────────────────────────
def _extract_page_title(page: Dict[str, Any]) -> str:
    try:
        properties = page.get("properties", {})

        for prop in properties.values():
            if prop.get("type") == "title":
                title_array = prop.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "Untitled")

        # fallback: sometimes no title property
        return page.get("url", "Untitled Page")

    except Exception:
        return "Untitled Page"


# ─────────────────────────────────────────────────────────────
# 3. SEARCH NOTION (FIXED)
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def search_notion(query: str) -> dict:
    notion = _get_notion_client()
    if not notion:
        return {"error": "Notion API not configured"}

    try:
        response = notion.search(
            query=query,
            filter={"property": "object", "value": "page"},
            page_size=10
        )

        results = response.get("results", [])

        parsed = []
        for r in results:
            parsed.append({
                "id": r.get("id"),
                "title": _extract_page_title(r),
                "url": r.get("url"),
                "last_edited": r.get("last_edited_time")
            })

        return {
            "query": query,
            "count": len(parsed),
            "results": parsed
        }

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# 4. RECURSIVE BLOCK FETCH (IMPORTANT FIX)
# ─────────────────────────────────────────────────────────────
def _fetch_all_blocks(notion, block_id: str) -> List[Dict]:
    all_blocks = []
    cursor = None

    while True:
        response = notion.blocks.children.list(
            block_id=block_id,
            start_cursor=cursor
        )

        results = response.get("results", [])
        all_blocks.extend(results)

        if not response.get("has_more"):
            break

        cursor = response.get("next_cursor")

    return all_blocks


# ─────────────────────────────────────────────────────────────
# 5. TEXT EXTRACTION (IMPROVED)
# ─────────────────────────────────────────────────────────────
def _extract_text(blocks: List[Dict]) -> str:
    text_lines = []

    for block in blocks:
        block_type = block.get("type")
        content = block.get(block_type, {})

        if "rich_text" in content:
            parts = [t.get("plain_text", "") for t in content["rich_text"]]
            line = "".join(parts).strip()

            if line:
                text_lines.append(line)

    return "\n".join(text_lines)


# ─────────────────────────────────────────────────────────────
# 6. READ PAGE (FULL FIX)
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def read_notion_page(page_id: str) -> dict:
    notion = _get_notion_client()
    if not notion:
        return {"error": "Notion API not configured"}

    try:
        blocks = _fetch_all_blocks(notion, page_id)

        if not blocks:
            return {
                "page_id": page_id,
                "content": "[No readable content found]"
            }

        text = _extract_text(blocks)

        return {
            "page_id": page_id,
            "content": text[:8000]  # prevent token explosion
        }

    except Exception as e:
        logger.error(f"Read failed: {str(e)}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# 7. RECENT PAGES (FIXED)
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def list_recent_notion_pages() -> dict:
    notion = _get_notion_client()
    if not notion:
        return {"error": "Notion API not configured"}

    try:
        response = notion.search(
            sort={"direction": "descending", "timestamp": "last_edited_time"},
            page_size=10
        )

        results = response.get("results", [])

        pages = []
        for r in results:
            pages.append({
                "id": r.get("id"),
                "title": _extract_page_title(r),
                "last_edited": r.get("last_edited_time")
            })

        return {"recent_pages": pages}

    except Exception as e:
        logger.error(f"Recent fetch failed: {str(e)}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# 8. RUN SERVER
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")