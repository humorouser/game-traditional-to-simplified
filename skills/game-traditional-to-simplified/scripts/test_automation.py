"""Boundary tests for the headless adapter, without using game data."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import auto_catalyst as auto


class AutomationTests(unittest.TestCase):
    def test_work_cannot_be_game_or_descendant(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)/'game'
            for path in (game,game/'nested'/'output'):
                with self.assertRaises(ValueError):
                    auto.outside_game(path,game)
            self.assertEqual(auto.outside_game(Path(tmp)/'game-tools',game), (Path(tmp)/'game-tools').resolve())

    def test_corrupt_cached_dependency_is_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/'tool.zip'; file.write_bytes(b'wrong')
            with patch('urllib.request.urlopen') as network:
                with self.assertRaises(ValueError):
                    auto.fetch('https://example.invalid/tool',file,'0'*64)
                network.assert_not_called()

    def test_unverified_archive_never_extracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'tool.zip'; archive.write_bytes(b'unknown')
            output = Path(tmp)/'sdk'
            with self.assertRaises(ValueError):
                auto.extract_verified(archive,output)
            self.assertFalse(output.exists())

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'tool.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('../escaped.dll',b'unsafe')
            with patch.object(auto,'EDITOR_HASH',hashlib.sha256(archive.read_bytes()).hexdigest()):
                with self.assertRaises(ValueError):
                    auto.extract_verified(archive,Path(tmp)/'sdk')
            self.assertFalse((Path(tmp)/'escaped.dll').exists())


if __name__=='__main__':
    unittest.main()
