"""
Symbolism lookup and cache management.
"""

import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from app.tools.catalog_tools import (
    build_base_tags,
    load_entity_dictionary,
    load_symbolism_cache,
    save_symbolism_cache,
)
from app.tools.http_fetch import HttpGetTool

logger = logging.getLogger(__name__)


class SymbolismService:
    """Load symbolism from cache or fetch via HTTP before caching the result."""

    def __init__(self, cache_path: str | None = None, lookup_url_template: str | None = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.cache_path = cache_path or str(base_dir / "cache" / "symbolism_cache.json")
        self.lookup_url_template = lookup_url_template or os.getenv(
            "SYMBOLISM_LOOKUP_URL_TEMPLATE",
            "https://httpbin.org/anything/symbolism?query={query}",
        )
        self.http_tool = HttpGetTool(max_text_length=1200)

    def get_symbolism(
        self,
        entity_type: str,
        name: str,
        category: str = "",
        article: str = "",
    ) -> dict[str, Any]:
        """Return symbolism from cache or fetch a fresh entry."""
        cache = load_symbolism_cache(self.cache_path)
        cached = cache.get(entity_type)
        if cached:
            return {
                "summary": cached.get("summary", ""),
                "keywords": cached.get("keywords", []),
                "source_note": cached.get("source_note", ""),
                "from_cache": True,
            }

        entities = load_entity_dictionary()
        entity_data = entities.get(entity_type, entities.get("unknown", {}))
        query = str(article).strip() or " ".join(
            part for part in [str(name).strip(), str(category).strip()] if part
        )

        http_ok = False
        if query:
            url = self.lookup_url_template.format(
                query=quote_plus(query),
                entity_type=quote_plus(entity_type),
                article=quote_plus(str(article).strip()),
            )
            http_ok, _ = self.http_tool.safe_run(url=url, timeout_sec=20)
            logger.info("Symbolism lookup for %s via %s -> %s", entity_type, url, http_ok)

        default_symbols = entity_data.get("default_symbolism", [])
        default_keywords = entity_data.get("default_keywords", [])
        display_name = entity_data.get("display_name_ru", entity_type)

        if not default_symbols and not default_keywords and not http_ok:
            raise ValueError("http_lookup_failed")

        summary = self._build_summary(display_name, default_symbols)
        keywords = self._build_keywords(
            entity_type=entity_type,
            category=category,
            article=article,
            default_keywords=default_keywords,
        )
        if http_ok:
            source_note = f"http_lookup:{query}"
        else:
            source_note = "default_entity_dictionary"

        cache[entity_type] = {
            "summary": summary,
            "keywords": keywords,
            "source_note": source_note,
        }
        save_symbolism_cache(cache, self.cache_path)

        return {
            "summary": summary,
            "keywords": keywords,
            "source_note": source_note,
            "from_cache": False,
        }

    @staticmethod
    def _build_summary(display_name: str, symbols: list[str]) -> str:
        """Build neutral symbolism summary text."""
        if not symbols:
            return f"{display_name.capitalize()} often seen as a decorative gift accent."

        joined = ", ".join(symbols[:3])
        return f"{display_name.capitalize()} is traditionally associated with {joined}."

    @staticmethod
    def _build_keywords(
        entity_type: str,
        category: str,
        article: str,
        default_keywords: list[str],
    ) -> list[str]:
        """Build cached symbolism keywords."""
        return build_base_tags(
            entity_type=entity_type,
            size_tag="",
            material="",
            category=category,
            article=article,
        )[:6] or default_keywords[:6]
