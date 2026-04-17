import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from kittycode.config.settings import KITTY_GLOBAL_DIR, KITTY_PROJECT_DIR

logger = logging.getLogger(__name__)

faiss = None
SentenceTransformer = None

VALID_CATEGORIES = {
    "identity",
    "project_context",
    "past_actions",
    "reflections",
    "bugs",
    "features",
    "general",
}
MAX_MEMORIES = 1000


class MemoryManager:
    """
    Structured memory store with optional semantic retrieval.

    Backends:
    - vector: FAISS + sentence-transformers available and model loaded
    - keyword: offline-safe lexical fallback when ML stack is unavailable
    """

    def __init__(self, max_memories: int = MAX_MEMORIES):
        self.max_memories = max_memories
        self.index_file = KITTY_PROJECT_DIR / "faiss.index"
        self.meta_file = KITTY_PROJECT_DIR / "memory_meta.json"
        self.legacy_file = KITTY_GLOBAL_DIR / "memory.json"

        self.metadata: List[Dict] = []
        self.graph: Dict[str, List[str]] = {}
        self._id_index: Dict[str, int] = {}

        self._model = None
        self._index = None
        self._dim = 384
        self._backend = "unknown"

        self._load_metadata()
        self._migrate_legacy_if_needed()

    # --- Backend and ML loading ---

    def _ensure_ml_loaded(self) -> bool:
        """Try to initialize vector backend. Returns True on success."""
        global faiss, SentenceTransformer

        backend_pref = os.getenv("KITTY_MEMORY_BACKEND", "keyword").strip().lower()
        if backend_pref not in {"vector", "auto"}:
            self._backend = "keyword"
            return False

        if self._backend == "vector":
            return True
        if self._backend == "keyword":
            return False

        try:
            import faiss as f
            import numpy as np  # noqa: F401
            from sentence_transformers import SentenceTransformer as ST

            faiss = f
            SentenceTransformer = ST
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

            allow_download = os.getenv("KITTY_MEMORY_ALLOW_DOWNLOAD", "0") == "1"
            self._model = SentenceTransformer(
                "all-MiniLM-L6-v2",
                local_files_only=not allow_download,
            )

            if self.index_file.exists():
                try:
                    self._index = faiss.read_index(str(self.index_file))
                except Exception:
                    self._index = faiss.IndexFlatL2(self._dim)
            else:
                self._index = faiss.IndexFlatL2(self._dim)

            if self._index.ntotal != len(self.metadata):
                self._index = faiss.IndexFlatL2(self._dim)
                if self.metadata:
                    texts = [m.get("text", "") for m in self.metadata]
                    embeddings = self._model.encode(texts)
                    self._index.add(np.array(embeddings).astype("float32"))

            self._backend = "vector"
            return True
        except Exception as e:
            logger.warning("Falling back to keyword memory backend: %s", e)
            self._backend = "keyword"
            self._model = None
            self._index = None
            return False

    # --- Persistence ---

    def _load_metadata(self):
        self.legacy_data = {"user_name": None}
        if self.meta_file.exists():
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw_memories = data.get("memories", [])
                self.legacy_data["user_name"] = data.get("user_name", None)
                self.graph = data.get("graph", {})

                self.metadata = []
                for m in raw_memories:
                    if isinstance(m, str):
                        self.metadata.append(
                            {
                                "id": str(uuid.uuid4())[:8],
                                "text": m,
                                "category": "general",
                                "timestamp": 0,
                                "links": [],
                            }
                        )
                    elif isinstance(m, dict):
                        self.metadata.append(self._normalize_entry(m))

                self._rebuild_id_index()
            except Exception as e:
                logger.error("Error loading memory metadata: %s", e)
                self.metadata = []

    def _normalize_entry(self, entry: Dict) -> Dict:
        result = dict(entry)
        result.setdefault("id", str(uuid.uuid4())[:8])
        result.setdefault("text", "")
        result.setdefault("category", "general")
        result.setdefault("timestamp", 0)
        result.setdefault("links", [])
        if result["category"] not in VALID_CATEGORIES:
            result["category"] = "general"
        return result

    def _migrate_legacy_if_needed(self):
        """
        Migrate old ~/.kittycode/memory.json structure into project scoped memory metadata.
        Migration runs only when project memory metadata is empty.
        """
        if self.metadata:
            return
        if not self.legacy_file.exists():
            return

        try:
            with open(self.legacy_file, "r", encoding="utf-8") as f:
                legacy = json.load(f)
        except Exception as e:
            logger.warning("Skipping legacy memory migration, could not read file: %s", e)
            return

        migrated = 0
        user_name = legacy.get("user_name")
        if user_name:
            self.legacy_data["user_name"] = user_name

        facts = legacy.get("facts", {}) if isinstance(legacy, dict) else {}
        if isinstance(facts, dict):
            for k, v in facts.items():
                if not isinstance(k, str):
                    continue
                text = f"{k}: {v}"
                if any(m.get("text") == text for m in self.metadata):
                    continue
                self.metadata.append(
                    {
                        "id": str(uuid.uuid4())[:8],
                        "text": text,
                        "category": "general",
                        "timestamp": time.time(),
                        "links": [],
                    }
                )
                migrated += 1

        self._rebuild_id_index()
        if migrated > 0 or user_name:
            logger.info("Migrated %s legacy memory entries", migrated)
            self._save_state()

    def _rebuild_id_index(self):
        self._id_index = {m["id"]: i for i, m in enumerate(self.metadata) if "id" in m}

    def _save_state(self):
        if self._backend == "vector" and self._index is not None and faiss is not None:
            try:
                faiss.write_index(self._index, str(self.index_file))
            except Exception as e:
                logger.warning("Failed writing FAISS index: %s", e)

        data_to_save = {
            "user_name": self.legacy_data.get("user_name"),
            "memories": self.metadata,
            "graph": self.graph,
        }
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)

    # --- Pruning ---

    def _rebuild_vector_index(self):
        if not (self._ensure_ml_loaded() and self.metadata):
            return
        import numpy as np

        self._index = faiss.IndexFlatL2(self._dim)
        texts = [m.get("text", "") for m in self.metadata]
        embeddings = self._model.encode(texts)
        self._index.add(np.array(embeddings).astype("float32"))

    def _prune(self):
        if len(self.metadata) <= self.max_memories:
            return

        protected_cats = {"identity", "reflections"}
        protected = [m for m in self.metadata if m.get("category") in protected_cats]
        prunable = [m for m in self.metadata if m.get("category") not in protected_cats]
        prunable.sort(key=lambda m: m.get("timestamp", 0), reverse=True)

        budget = self.max_memories - len(protected)
        kept = protected + prunable[: max(0, budget)]

        kept_ids = {m["id"] for m in kept if "id" in m}
        self.graph = {
            k: [v for v in links if v in kept_ids]
            for k, links in self.graph.items()
            if k in kept_ids
        }

        kept.sort(key=lambda m: m.get("timestamp", 0))
        self.metadata = kept
        self._rebuild_id_index()
        self._rebuild_vector_index()

    # --- Graph operations ---

    def link_memories(self, id_a: str, id_b: str):
        if id_a not in self._id_index or id_b not in self._id_index:
            return
        self.graph.setdefault(id_a, [])
        self.graph.setdefault(id_b, [])
        if id_b not in self.graph[id_a]:
            self.graph[id_a].append(id_b)
        if id_a not in self.graph[id_b]:
            self.graph[id_b].append(id_a)
        self._save_state()

    def _get_graph_neighbors(self, memory_ids: List[str], depth: int = 1) -> List[str]:
        visited = set(memory_ids)
        frontier = list(memory_ids)

        for _ in range(depth):
            next_frontier = []
            for mid in frontier:
                for neighbor in self.graph.get(mid, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.append(neighbor)
            frontier = next_frontier

        results = []
        for mid in visited:
            idx = self._id_index.get(mid)
            if idx is not None and idx < len(self.metadata):
                results.append(self.metadata[idx].get("text", ""))
        return results

    # --- Keyword fallback ---

    def _keyword_search(self, query: str, k: int) -> List[int]:
        tokens = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 1}
        if not tokens:
            return list(range(max(0, len(self.metadata) - k), len(self.metadata)))

        scored = []
        for i, entry in enumerate(self.metadata):
            text = str(entry.get("text", "")).lower()
            score = sum(1 for t in tokens if t in text)
            if score > 0:
                scored.append((score, entry.get("timestamp", 0), i))

        if not scored:
            return list(range(max(0, len(self.metadata) - k), len(self.metadata)))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [idx for _, _, idx in scored[:k]]

    # --- Public API ---

    def get(self, key, default=None):
        if key == "user_name":
            return self.legacy_data.get("user_name", default)
        return default

    def set(self, key, value):
        if key == "user_name":
            self.legacy_data["user_name"] = value
            self._save_state()

    def set_fact(self, key, value, category="general", link_to: Optional[str] = None):
        cat = category if category in VALID_CATEGORIES else "general"
        text = f"{key}: {value}"

        if any(m.get("text") == text for m in self.metadata):
            return None

        mem_id = str(uuid.uuid4())[:8]
        entry = {
            "id": mem_id,
            "text": text,
            "category": cat,
            "timestamp": time.time(),
            "links": [],
        }

        vector_ready = self._ensure_ml_loaded()
        if vector_ready:
            import numpy as np

            embedding = self._model.encode([text])
            self._index.add(np.array(embedding).astype("float32"))

        self.metadata.append(entry)
        self._id_index[mem_id] = len(self.metadata) - 1

        if link_to and link_to in self._id_index:
            self.link_memories(mem_id, link_to)
            entry["links"].append(link_to)

        self._prune()
        self._save_state()
        return mem_id

    def list_memories(self, limit: int = 10, category: str = "") -> List[Dict]:
        items = self.metadata[-max(1, limit):]
        if category:
            items = [m for m in items if m.get("category") == category]
        return items

    def find_memory_entries(self, query: str, limit: int = 10) -> List[Dict]:
        if not query.strip():
            return self.list_memories(limit=limit)

        texts = self.get_relevant_context(query, k=limit)
        if not texts:
            return []

        by_text: Dict[str, Dict] = {}
        for m in self.metadata:
            t = str(m.get("text", ""))
            by_text[t] = m

        results = []
        for t in texts:
            entry = by_text.get(t)
            if entry:
                results.append(entry)
        return results[:limit]

    def prune_memories(self, max_memories: Optional[int] = None, dedupe: bool = True) -> Dict[str, int]:
        original = len(self.metadata)

        if dedupe:
            deduped = []
            seen = set()
            for m in sorted(self.metadata, key=lambda x: x.get("timestamp", 0), reverse=True):
                txt = m.get("text", "")
                if txt in seen:
                    continue
                seen.add(txt)
                deduped.append(m)
            deduped.reverse()
            self.metadata = deduped
            self._rebuild_id_index()

        if max_memories is not None and max_memories > 0:
            self.max_memories = max_memories

        self._prune()
        self._save_state()

        return {
            "before": original,
            "after": len(self.metadata),
            "removed": max(0, original - len(self.metadata)),
        }

    def export_memories(self, export_path: Path) -> Dict[str, str]:
        payload = {
            "user_name": self.legacy_data.get("user_name"),
            "backend": self.backend,
            "count": len(self.metadata),
            "memories": self.metadata,
            "graph": self.graph,
        }
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return {"path": str(export_path), "count": str(len(self.metadata))}

    def get_relevant_context(self, query: str, k: int = 5) -> List[str]:
        if not self.metadata:
            return []

        search_k = min(k, len(self.metadata))
        if search_k <= 0:
            return []

        semantic_ids = []
        semantic_texts = []

        if self._ensure_ml_loaded():
            import numpy as np

            query_embedding = self._model.encode([query])
            _, indices = self._index.search(np.array(query_embedding).astype("float32"), search_k)
            for idx in indices[0]:
                if idx != -1 and idx < len(self.metadata):
                    mem = self.metadata[idx]
                    semantic_ids.append(mem.get("id"))
                    semantic_texts.append(mem.get("text", ""))
        else:
            ranked = self._keyword_search(query, search_k)
            for idx in ranked:
                mem = self.metadata[idx]
                semantic_ids.append(mem.get("id"))
                semantic_texts.append(mem.get("text", ""))

        neighbor_texts = self._get_graph_neighbors([mid for mid in semantic_ids if mid], depth=1) if semantic_ids else []

        seen = set()
        results = []
        for t in semantic_texts + neighbor_texts:
            if t and t not in seen:
                seen.add(t)
                results.append(t)
        return results

    def get_facts(self):
        return {
            f"fact_{i}": m["text"] if isinstance(m, dict) else m
            for i, m in enumerate(self.metadata[-10:])
        }

    def save(self):
        self._save_state()

    @property
    def backend(self) -> str:
        if self._backend == "unknown":
            self._ensure_ml_loaded()
        return self._backend
