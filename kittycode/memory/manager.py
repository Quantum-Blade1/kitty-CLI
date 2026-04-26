import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from kittycode.config.settings import KITTY_GLOBAL_DIR, KITTY_PROJECT_DIR
from kittycode.security.vault import MemoryVault
from kittycode.memory.graph import KnowledgeGraph, NodeType
from kittycode.memory.decay import DecayEngine

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
        self._legacy_links: Dict[str, List[str]] = {}
        self._id_index: Dict[str, int] = {}

        self._model = None
        self._index = None
        self._dim = 384
        self._backend = "unknown"
        self.vault = MemoryVault()
        self._graph = KnowledgeGraph()
        self._decay = DecayEngine()
        self._graph_file = KITTY_PROJECT_DIR / "knowledge_graph.json"

        self._load_metadata()
        self._load_graph()
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
                self._legacy_links = data.get("graph", {})

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
            "graph": self._legacy_links,
        }
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)

    def _load_graph(self):
        if self._graph_file.exists():
            try:
                import json
                data = json.loads(self._graph_file.read_text(encoding="utf-8"))
                self._graph = KnowledgeGraph.from_dict(data)
                self._decay.apply_decay(self._graph)
            except Exception as e:
                logger.warning("Graph load failed, starting fresh: %s", e)

    def _save_graph(self):
        try:
            import json
            self._graph_file.write_text(
                json.dumps(self._graph.to_dict(), indent=2, default=str),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Graph save failed: %s", e)

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
        self._legacy_links = {
            k: [v for v in links if v in kept_ids]
            for k, links in self._legacy_links.items()
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
        self._legacy_links.setdefault(id_a, [])
        self._legacy_links.setdefault(id_b, [])
        if id_b not in self._legacy_links[id_a]:
            self._legacy_links[id_a].append(id_b)
        if id_a not in self._legacy_links[id_b]:
            self._legacy_links[id_b].append(id_a)
        
        # Also mirror to the new knowledge graph
        from kittycode.memory.graph import EdgeType
        self._graph.add_edge(id_a, id_b, EdgeType.RELATES_TO)
        
        self._save_state()

    def _get_graph_neighbor_texts(self, memory_ids: List[str], depth: int = 1) -> List[str]:
        visited = set(memory_ids)
        frontier = list(memory_ids)

        for _ in range(depth):
            next_frontier = []
            for mid in frontier:
                for neighbor in self._legacy_links.get(mid, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.append(neighbor)
            frontier = next_frontier

        results = []
        for mid in visited:
            idx = self._id_index.get(mid)
            if idx is not None and idx < len(self.metadata):
                results.append(self._decrypt_entry(self.metadata[idx]))
        return results

    def _keyword_search(self, query: str, k: int, pool: List[Dict] = None) -> List[int]:
        if pool is None:
            pool = self.metadata
        tokens = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 1}
        if not tokens:
            return list(range(max(0, len(pool) - k), len(pool)))

        scored = []
        for i, entry in enumerate(pool):
            text = str(entry.get("text", "")).lower()
            score = sum(1 for t in tokens if t in text)
            if score > 0:
                scored.append((score, entry.get("timestamp", 0), i))

        if not scored:
            return list(range(max(0, len(pool) - k), len(pool)))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [idx for _, _, idx in scored[:k]]

    # --- Public API ---

    def get(self, key, default=None):
        if key == "user_name":
            return self.legacy_data.get("user_name", default)
        
        # Fallback to searching through facts (key: value format) - Latest first
        for m in reversed(self.metadata):
            text = self._decrypt_entry(m)
            if text.startswith(f"{key}: "):
                return text.split(f"{key}: ", 1)[1]

        
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
        
        # Identity and secret categories are always encrypted
        storage_text = text
        if cat in ("identity", "secret"):
            storage_text = self.vault.encrypt(f"{key}: {value}")
            
        entry = {
            "id": mem_id,
            "text": storage_text,
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
        
        # Infer node type from category
        type_map = {
            "bugs":            NodeType.BUG,
            "features":        NodeType.FEATURE,
            "identity":        NodeType.PERSON,
            "project_context": NodeType.CONCEPT,
            "reflections":     NodeType.CONCEPT,
            "general":         NodeType.FACT,
        }
        ntype = type_map.get(cat, NodeType.FACT)
        self._graph.add_node(label=f"{key}: {value}", node_type=ntype, weight=1.0, node_id=mem_id)
        self.save()
        
        return mem_id

    def list_memories(self, limit: int = 10, category: str = "") -> list:
        items = self.metadata  # all memories, most recent last
        if category:
            items = [m for m in items if m.get("category") == category]
        return items[-limit:] if limit > 0 else items

    def find_memory_entries(self, query: str, limit: int = 10) -> List[Dict]:
        if not query.strip():
            return self.list_memories(limit=limit)

        texts = self.get_relevant_context(query, k=limit)
        if not texts:
            return []

        lookup: Dict[str, Dict] = {}
        for m in self.metadata:
            lookup[str(m.get("text"))] = m
            lookup[self._decrypt_entry(m)] = m

        results = []
        for t in texts:
            entry = lookup.get(t)
            if entry:
                results.append(entry)

        seen_ids = set()
        final_results = []
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                final_results.append(r)
        return final_results[:limit]

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
            "graph": self._legacy_links,
        }
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return {"path": str(export_path), "count": str(len(self.metadata))}

    def _decrypt_entry(self, entry: Dict) -> str:
        text = str(entry.get("text", ""))
        if entry.get("category") in ("identity", "secret"):
            try:
                return self.vault.decrypt(text)
            except Exception:
                return f"[Decryption Error] {text[:20]}..."
        return text

    def get_relevant_context(self, query: str, k: int = 5) -> List[str]:
        if not self.metadata or not query.strip():
            return []

        search_k = min(k, len(self.metadata))
        if search_k <= 0:
            return []

        # Quantum amplitude amplification pre-filter
        # Narrows the candidate set before FAISS or keyword search
        from kittycode.quantum.memory_q import quantum_retrieve
        candidate_pool = quantum_retrieve(query, self.metadata, k=min(k*3, len(self.metadata)))

        semantic_ids = []
        semantic_texts = []

        if self._ensure_ml_loaded():
            import numpy as np
            import faiss

            tmp_index = faiss.IndexFlatL2(self._dim)
            texts = [m.get("text", "") for m in candidate_pool]
            embeddings = self._model.encode(texts)
            tmp_index.add(np.array(embeddings).astype("float32"))

            query_embedding = self._model.encode([query])
            _, indices = tmp_index.search(np.array(query_embedding).astype("float32"), min(search_k, len(candidate_pool)))
            for idx in indices[0]:
                if idx != -1 and idx < len(candidate_pool):
                    mem = candidate_pool[idx]
                    semantic_ids.append(mem.get("id"))
                    semantic_texts.append(self._decrypt_entry(mem))
        else:
            ranked = self._keyword_search(query, search_k, pool=candidate_pool)
            for idx in ranked:
                mem = candidate_pool[idx]
                semantic_ids.append(mem.get("id"))
                semantic_texts.append(self._decrypt_entry(mem))

        neighbor_texts = self._get_graph_neighbor_texts([mid for mid in semantic_ids if mid], depth=1) if semantic_ids else []

        seed_ids = [mid for mid in semantic_ids if mid and mid in self._graph.nodes]
        if seed_ids:
            activated = self._graph.spreading_activation(seed_ids, depth=2, top_k=k)
            # Reinforce retrieved nodes
            for node in activated:
                self._decay.reinforce(node)
            activated_texts = [node.label for node in activated]
        else:
            activated_texts = []

        seen = set()
        results = []
        for t in semantic_texts + activated_texts + neighbor_texts:
            if t and t not in seen:
                seen.add(t)
                results.append(t)
        return results[:k * 2]   # return up to 2k since graph adds context

    def get_facts(self):
        return {
            f"fact_{i}": m["text"] if isinstance(m, dict) else m
            for i, m in enumerate(self.metadata[-10:])
        }

    def save(self):
        self._save_state()
        self._save_graph()

    @property
    def graph(self) -> KnowledgeGraph:
        return self._graph

    @property
    def backend(self) -> str:
        if self._backend == "unknown":
            self._ensure_ml_loaded()
        return self._backend
