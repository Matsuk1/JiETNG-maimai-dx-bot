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


class ComponentMemoryTests(unittest.TestCase):
    def test_browser_descendants_are_aggregated_without_changing_main_rss(self):
        from unittest.mock import MagicMock
        from modules.memory_manager import get_process_memory_stats
        def process(pid, parent, mb, argv):
            item = MagicMock(pid=pid)
            item.ppid.return_value = parent
            item.memory_info.return_value.rss = mb * 1024 ** 2
            item.cmdline.return_value = argv
            return item
        root = process(1, 0, 100, ['python', 'main.py'])
        driver = process(2, 1, 20, ['/app/playwright/node'])
        browser = process(3, 2, 30, ['utility'])
        ocr = process(4, 1, 200, ['python', '/app/table_model.py'])
        root.children.return_value = [browser, ocr, driver]
        with patch('modules.memory_manager.psutil.Process', return_value=root):
            stats = get_process_memory_stats()
        groups = {row['key']: row for row in stats['memory_components']}
        self.assertEqual(groups['playwright']['memory_mb'], 50)
        self.assertEqual(groups['ocr']['memory_mb'], 200)
        self.assertEqual(stats['process_memory_mb'], 100)
        self.assertEqual(stats['process_tree_memory_mb'], 350)
