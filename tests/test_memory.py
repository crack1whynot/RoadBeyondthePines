import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.memory.memory import InMemoryStore, ProjectMemory
from backend.memory.memory_entry import MemoryEntry
from backend.memory.memory_query import MemoryQuery


class MemoryLayerTests(unittest.TestCase):
    def test_store_update_search_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InMemoryStore()
            memory = ProjectMemory(storage_path=str(Path(temp_dir) / "memory.json"), store=store)

            entry = MemoryEntry(
                id="entry-1",
                title="Architecture note",
                category="documentation",
                tags=["architecture", "backend"],
                content="The Brain layer reasons; the Runtime executes.",
                author="developer",
                source="docs",
            )
            memory.store_entry(entry)

            updated = MemoryEntry(
                id="entry-1",
                title="Architecture note",
                category="documentation",
                tags=["architecture", "backend"],
                content="The Brain layer reasons; the Runtime executes; Memory persists knowledge.",
                author="developer",
                source="docs",
            )
            memory.update_entry(updated)

            results = memory.search_entries(MemoryQuery(category="documentation", tag="backend", author="developer"))
            self.assertEqual(len(results), 1)
            self.assertIn("Memory persists knowledge", results[0].content)

            snapshot = memory.create_snapshot("snapshot-1")
            self.assertEqual(snapshot.id, "snapshot-1")
            self.assertEqual(len(snapshot.entries), 1)


if __name__ == "__main__":
    unittest.main()
