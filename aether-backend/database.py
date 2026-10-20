"""
In-memory database that mimics Motor/MongoDB async API.
Drop-in replacement — when you're ready for real MongoDB, just swap this file back.
"""
import copy
import re
from typing import Any, Dict, List, Optional


class InMemoryCursor:
    """Mimics Motor's async cursor with sort and to_list."""
    def __init__(self, docs: List[Dict]):
        self._docs = list(docs)
        self._sort_key = None
        self._sort_dir = 1

    def sort(self, key: str, direction: int = 1):
        self._sort_key = key
        self._sort_dir = direction
        return self

    async def to_list(self, length: int = 100) -> List[Dict]:
        docs = list(self._docs)
        if self._sort_key:
            docs.sort(
                key=lambda d: d.get(self._sort_key, ""),
                reverse=(self._sort_dir == -1),
            )
        return docs[:length]


class InMemoryCollection:
    """Mimics a Motor collection with basic CRUD operations."""
    def __init__(self, name: str):
        self.name = name
        self._docs: List[Dict] = []
        self._indexes: List[Dict] = []

    def _matches(self, doc: Dict, query: Dict) -> bool:
        for key, value in query.items():
            if key == "$or":
                if not any(self._matches(doc, sub) for sub in value):
                    return False
                continue
            doc_val = doc.get(key)
            if isinstance(value, dict):
                for op, op_val in value.items():
                    if op == "$in" and doc_val not in op_val:
                        return False
                    if op == "$regex":
                        flags = value.get("$options", "")
                        re_flags = re.IGNORECASE if "i" in flags else 0
                        if not re.search(op_val, str(doc_val or ""), re_flags):
                            return False
            else:
                if doc_val != value:
                    return False
        return True

    def find(self, query: Optional[Dict] = None) -> InMemoryCursor:
        query = query or {}
        matched = [copy.deepcopy(d) for d in self._docs if self._matches(d, query)]
        return InMemoryCursor(matched)

    async def find_one(self, query: Dict) -> Optional[Dict]:
        for d in self._docs:
            if self._matches(d, query):
                return copy.deepcopy(d)
        return None

    async def insert_one(self, doc: Dict):
        self._docs.append(copy.deepcopy(doc))

    async def insert_many(self, docs: List[Dict]):
        for doc in docs:
            self._docs.append(copy.deepcopy(doc))

    async def update_one(self, query: Dict, update: Dict, upsert: bool = False):
        for i, d in enumerate(self._docs):
            if self._matches(d, query):
                if "$set" in update:
                    self._docs[i].update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        self._docs[i][k] = self._docs[i].get(k, 0) + v
                return
        if upsert and "$set" in update:
            new_doc = {**query, **update["$set"]}
            self._docs.append(new_doc)

    async def delete_one(self, query: Dict):
        for i, d in enumerate(self._docs):
            if self._matches(d, query):
                self._docs.pop(i)
                return

    async def delete_many(self, query: Dict):
        self._docs = [d for d in self._docs if not self._matches(d, query)]

    async def count_documents(self, query: Dict) -> int:
        return sum(1 for d in self._docs if self._matches(d, query))

    async def create_index(self, keys, **kwargs):
        """No-op for in-memory — indexes aren't needed."""
        pass


class InMemoryDatabase:
    """Mimics a Motor database with collection access."""
    def __init__(self):
        self._collections: Dict[str, InMemoryCollection] = {}

    def __getitem__(self, name: str) -> InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = InMemoryCollection(name)
        return self._collections[name]


# Singleton instance
_db = InMemoryDatabase()


def get_db() -> InMemoryDatabase:
    return _db
