import unittest
from unittest.mock import patch
from modules.memory_manager import MemoryManager

class MemoryCleanupTests(unittest.TestCase):
    def test_one_full_collection_and_cache_callbacks(self):
        manager=MemoryManager()
        called=[]
        manager.register_cleanup(lambda: called.append(True))
        with patch('modules.memory_manager.gc.collect',return_value=3) as collect:
            stats=manager.cleanup()
        collect.assert_called_once_with(2)
        self.assertEqual(stats['collected_objects'],3)
        self.assertEqual(called,[True])
