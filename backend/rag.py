"""WCAG retrieval with curated axe mappings and optional local embeddings.

FAISS and Sentence Transformers are optional. When they are installed, the
service embeds the local WCAG corpus and performs cosine-similarity search with
FAISS. Otherwise it falls back to a small TF-IDF lexical ranker.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any

DATA_PATH = Path(__file__).parent / "data" / "wcag.json"
EMBEDDING_MODEL = os.getenv("A11YLENS_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LOGGER = logging.getLogger(__name__)

RULE_TO_CRITERIA: dict[str, list[str]] = {
    "image-alt": ["1.1.1"],
    "image-redundant-alt": ["1.1.1"],
    "role-img-alt": ["1.1.1"],
    "color-contrast": ["1.4.3"],
    "document-title": ["2.4.2"],
    "link-name": ["2.4.4"],
    "heading-order": ["1.3.1"],
    "aria-required-children": ["1.3.1"],
    "html-has-lang": ["3.1.1"],
    "label": ["3.3.2", "4.1.2"],
    "select-name": ["3.3.2", "4.1.2"],
    "input-button-name": ["4.1.2"],
    "button-name": ["4.1.2"],
    "aria-input-field-name": ["4.1.2"],
    "aria-hidden-focus": ["4.1.2"],
    "duplicate-id-aria": ["4.1.2"],
}

STOP_WORDS = {
    "a", "about", "after", "all", "an", "and", "are", "as", "at", "be",
    "by", "can", "for", "from", "has", "have", "in", "into", "is", "it",
    "of", "on", "or", "page", "should", "that", "the", "their", "this",
    "to", "user", "users", "was", "when", "where", "which", "with",
}


@dataclass(frozen=True)
class RetrievalResult:
    criteria: tuple[dict[str, str], ...]
    method: str


@lru_cache(maxsize=1)
def load_criteria() -> tuple[dict[str, str], ...]:
    with DATA_PATH.open(encoding="utf-8") as data_file:
        records = json.load(data_file)
    return tuple(records)


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in STOP_WORDS
    ]


def _lexical_rank(query: str, criteria: tuple[dict[str, str], ...]) -> list[dict[str, str]]:
    documents = [
        _tokens(f"{item['id']} {item['title']} {item['summary']}")
        for item in criteria
    ]
    document_frequency = Counter(term for document in documents for term in set(document))
    total_documents = max(len(documents), 1)
    inverse_frequency = {
        term: math.log(1 + (total_documents + 1) / (frequency + 1))
        for term, frequency in document_frequency.items()
    }
    query_counts = Counter(_tokens(query))
    query_weights = {
        term: (1 + math.log(count)) * inverse_frequency.get(term, 0.0)
        for term, count in query_counts.items()
    }
    query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values())) or 1.0

    scored: list[tuple[float, int]] = []
    for index, document in enumerate(documents):
        counts = Counter(document)
        weights = {
            term: (1 + math.log(count)) * inverse_frequency[term]
            for term, count in counts.items()
            if term in inverse_frequency
        }
        norm = math.sqrt(sum(weight * weight for weight in weights.values())) or 1.0
        score = sum(query_weights.get(term, 0.0) * weight for term, weight in weights.items())
        if score:
            scored.append((score / (query_norm * norm), index))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [criteria[index] for _, index in scored]


_VECTOR_LOCK = Lock()
_VECTOR_ATTEMPTED = False
_VECTOR_BACKEND: tuple[Any, Any, tuple[dict[str, str], ...]] | None = None


def _get_vector_backend() -> tuple[Any, Any, tuple[dict[str, str], ...]] | None:
    """Load the optional model and in-memory FAISS index once per API process."""

    global _VECTOR_ATTEMPTED, _VECTOR_BACKEND
    if _VECTOR_ATTEMPTED:
        return _VECTOR_BACKEND

    with _VECTOR_LOCK:
        if _VECTOR_ATTEMPTED:
            return _VECTOR_BACKEND
        _VECTOR_ATTEMPTED = True
        criteria = load_criteria()
        try:
            import faiss
            import numpy as np
            from sentence_transformers import SentenceTransformer
        except Exception as error:
            LOGGER.info("Semantic WCAG retrieval is unavailable: %s", error)
            return None

        try:
            model = SentenceTransformer(EMBEDDING_MODEL)
            documents = [
                f"WCAG {item['id']} {item['title']}. {item['summary']}"
                for item in criteria
            ]
            embeddings = model.encode(
                documents,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            embeddings = np.asarray(embeddings, dtype="float32")
            index = faiss.IndexFlatIP(int(embeddings.shape[1]))
            index.add(embeddings)
            _VECTOR_BACKEND = (model, index, criteria)
        except Exception:
            LOGGER.exception("Could not load the local embedding model; using TF-IDF retrieval.")
        return _VECTOR_BACKEND


def _vector_rank(query: str, backend: tuple[Any, Any, tuple[dict[str, str], ...]]) -> list[dict[str, str]]:
    import numpy as np

    model, index, criteria = backend
    query_vector = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    query_vector = np.asarray(query_vector, dtype="float32")
    _scores, indices = index.search(query_vector, len(criteria))
    return [criteria[index] for index in indices[0] if 0 <= index < len(criteria)]


def retrieve_criteria(
    rule_id: str,
    description: str,
    limit: int = 3,
    context: str = "",
) -> RetrievalResult:
    """Prefer curated axe mappings, then fill from semantic or lexical search."""

    criteria = load_criteria()
    by_id = {criterion["id"]: criterion for criterion in criteria}
    selected: list[dict[str, str]] = []
    for criterion_id in RULE_TO_CRITERIA.get(rule_id, []):
        criterion = by_id.get(criterion_id)
        if criterion and criterion not in selected and len(selected) < limit:
            selected.append(criterion)

    query = " ".join(part for part in (rule_id, description, context) if part).strip()
    backend = _get_vector_backend()
    if backend:
        ranked = _vector_rank(query, backend)
        method = "FAISS cosine-similarity embeddings plus axe rule mapping"
    else:
        ranked = _lexical_rank(query, criteria)
        method = "TF-IDF lexical retrieval plus axe rule mapping"

    selected_ids = {criterion["id"] for criterion in selected}
    for criterion in ranked:
        if criterion["id"] in selected_ids:
            continue
        selected.append(criterion)
        selected_ids.add(criterion["id"])
        if len(selected) >= limit:
            break
    return RetrievalResult(tuple(selected), method)

