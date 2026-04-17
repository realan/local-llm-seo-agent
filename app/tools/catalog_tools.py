"""
Catalog-specific tools and helpers.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENTITY_DICT_PATH = BASE_DIR / "data" / "entity_dictionary.yaml"
SIZE_RULES_PATH = BASE_DIR / "data" / "size_rules.yaml"
CACHE_PATH = BASE_DIR / "cache" / "symbolism_cache.json"


def normalize_text(value: Any) -> str:
    """Normalize free text for matching."""
    return str(value or "").strip().lower().replace("ё", "е")


@lru_cache(maxsize=1)
def load_entity_dictionary(path: str = str(ENTITY_DICT_PATH)) -> dict[str, Any]:
    """Load entity dictionary from YAML."""
    with open(path, "r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload.get("entities", {})


@lru_cache(maxsize=1)
def load_size_rules(path: str = str(SIZE_RULES_PATH)) -> dict[str, Any]:
    """Load size rules from YAML."""
    with open(path, "r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload.get("size_rules", {})


def parse_optional_float(value: Any) -> Optional[float]:
    """Parse numeric field or return None when value is invalid."""
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def detect_entity_type(name: str, category: str = "") -> dict[str, str]:
    """Detect entity type using alias dictionary first and heuristics second."""
    name_norm = normalize_text(name)
    category_norm = normalize_text(category)
    entities = load_entity_dictionary()

    exact_candidates = []
    partial_candidates = []
    for entity_type, item in entities.items():
        if entity_type == "unknown":
            continue
        aliases = [normalize_text(alias) for alias in item.get("aliases", [])]
        category_hints = [normalize_text(hint) for hint in item.get("category_hints", [])]

        for alias in aliases:
            if alias and alias == name_norm:
                exact_candidates.append((entity_type, alias))
            elif alias and alias in name_norm:
                partial_candidates.append((entity_type, alias, len(alias)))

        if category_norm and any(hint in category_norm for hint in category_hints):
            for alias in aliases:
                if alias and alias in name_norm:
                    return {
                        "entity_type": entity_type,
                        "confidence": "high",
                        "matched_alias": alias,
                    }

    if exact_candidates:
        entity_type, alias = exact_candidates[0]
        return {"entity_type": entity_type, "confidence": "high", "matched_alias": alias}

    if partial_candidates:
        partial_candidates.sort(key=lambda item: item[2], reverse=True)
        entity_type, alias, _ = partial_candidates[0]
        confidence = "medium" if len(alias) >= 4 else "low"
        return {
            "entity_type": entity_type,
            "confidence": confidence,
            "matched_alias": alias,
        }

    return {"entity_type": "unknown", "confidence": "low", "matched_alias": ""}


def classify_size(name: str, height_cm: Any = None, weight_g: Any = None) -> dict[str, str]:
    """Classify souvenir size using title hints and numeric thresholds."""
    rules = load_size_rules()
    hints = rules.get("title_hints", {})
    name_norm = normalize_text(name)
    height = parse_optional_float(height_cm)
    weight = parse_optional_float(weight_g)

    small_hints = [normalize_text(item) for item in hints.get("small", [])]
    medium_hints = [normalize_text(item) for item in hints.get("medium", [])]
    large_hints = [normalize_text(item) for item in hints.get("large", [])]

    hinted_size = None
    if any(hint in name_norm for hint in small_hints):
        hinted_size = ("small", "title_hint_small")
    elif any(hint in name_norm for hint in large_hints):
        hinted_size = ("large", "title_hint_large")
    elif any(hint in name_norm for hint in medium_hints):
        hinted_size = ("medium", "title_hint_medium")

    numeric_size = None
    numeric_reason = None
    if weight is not None:
        if weight < 100:
            numeric_size = "small"
            numeric_reason = "weight_small"
        elif weight > 1000:
            numeric_size = "large"
            numeric_reason = "weight_large"
    if numeric_size is None and height is not None:
        if height <= 7:
            numeric_size = "small"
            numeric_reason = "height_small"
        elif height > 15:
            numeric_size = "large"
            numeric_reason = "height_large"
        else:
            numeric_size = "medium"
            numeric_reason = "height_medium"
    elif numeric_size is None and weight is not None:
        numeric_size = "medium"
        numeric_reason = "weight_medium"

    if hinted_size and numeric_size and hinted_size[0] != numeric_size:
        return {"size_tag": numeric_size, "size_reason": f"{hinted_size[1]} + {numeric_reason}"}

    if hinted_size:
        if numeric_reason:
            return {"size_tag": hinted_size[0], "size_reason": f"{hinted_size[1]} + {numeric_reason}"}
        return {"size_tag": hinted_size[0], "size_reason": hinted_size[1]}

    if numeric_size:
        return {"size_tag": numeric_size, "size_reason": numeric_reason}

    return {"size_tag": "medium", "size_reason": "fallback_default"}


def build_base_tags(
    entity_type: str,
    size_tag: str,
    material: str = "",
    category: str = "",
    article: str = "",
) -> list[str]:
    """Build deterministic base tags for SEO prompt context."""
    entities = load_entity_dictionary()
    entity_data = entities.get(entity_type, entities.get("unknown", {}))
    tags = list(entity_data.get("default_keywords", []))
    if entity_type and entity_type != "unknown":
        tags.append(entity_data.get("display_name_ru", entity_type))
    if size_tag:
        tags.append(size_tag)
    if material:
        tags.append(normalize_text(material))
    if category:
        tags.append(normalize_text(category))
    if article:
        tags.append(str(article).strip())

    deduped = []
    seen = set()
    for tag in tags:
        clean = str(tag).strip()
        if clean and clean not in seen:
            seen.add(clean)
            deduped.append(clean)
    return deduped


def load_symbolism_cache(cache_path: str = str(CACHE_PATH)) -> dict[str, Any]:
    """Load local symbolism cache from JSON."""
    path = Path(cache_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_symbolism_cache(payload: dict[str, Any], cache_path: str = str(CACHE_PATH)) -> None:
    """Persist local symbolism cache to JSON."""
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


class DetectEntityTypeTool(BaseTool):
    """Tool wrapper around entity detection helper."""

    def __init__(self):
        super().__init__("detect_entity_type", "detect base figurine type using dictionary aliases")

    def run(self, name: str, category: str = "") -> dict[str, Any]:
        return detect_entity_type(name=name, category=category)


class ClassifySizeTool(BaseTool):
    """Tool wrapper around size classification helper."""

    def __init__(self):
        super().__init__("classify_size", "classify item size using height, weight, and name hints")

    def run(self, name: str, height_cm: Any = None, weight_g: Any = None) -> dict[str, Any]:
        return classify_size(name=name, height_cm=height_cm, weight_g=weight_g)


class BuildBaseTagsTool(BaseTool):
    """Build deterministic tags for LLM context."""

    def __init__(self):
        super().__init__("build_base_tags", "build base SEO tags from entity, size, material, and category")

    def run(
        self,
        entity_type: str,
        size_tag: str,
        material: str = "",
        category: str = "",
        article: str = "",
    ) -> dict[str, Any]:
        return {
            "tags": build_base_tags(
                entity_type=entity_type,
                size_tag=size_tag,
                material=material,
                category=category,
                article=article,
            )
        }


class LoadSymbolismCacheTool(BaseTool):
    """Load one entry from symbolism cache."""

    def __init__(self, cache_path: str = str(CACHE_PATH)):
        super().__init__("load_symbolism_cache", "load cached symbolism by entity type")
        self.cache_path = cache_path

    def run(self, entity_type: str) -> dict[str, Any]:
        cache = load_symbolism_cache(self.cache_path)
        entry = cache.get(entity_type)
        if not entry:
            return {"found": False, "summary": "", "keywords": [], "source_note": ""}
        return {
            "found": True,
            "summary": entry.get("summary", ""),
            "keywords": entry.get("keywords", []),
            "source_note": entry.get("source_note", ""),
        }


class SaveSymbolismCacheTool(BaseTool):
    """Persist one entry to symbolism cache."""

    def __init__(self, cache_path: str = str(CACHE_PATH)):
        super().__init__("save_symbolism_cache", "save symbolism into local cache")
        self.cache_path = cache_path

    def run(
        self,
        entity_type: str,
        summary: str,
        keywords: list[str],
        source_note: str,
    ) -> dict[str, Any]:
        cache = load_symbolism_cache(self.cache_path)
        cache[entity_type] = {
            "summary": summary,
            "keywords": keywords,
            "source_note": source_note,
        }
        save_symbolism_cache(cache, self.cache_path)
        return {"success": True}
