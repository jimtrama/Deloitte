import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


CONFIG_FILE = Path(__file__).resolve().parents[1] / "config.py"


class ConfigurationTests(unittest.TestCase):
    def test_local_default_preserves_native_ollama_connection(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = runpy.run_path(str(CONFIG_FILE))
        self.assertEqual(settings["OLLAMA_HOST"], "http://localhost:11434")

    def test_docker_service_address_can_be_selected(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://ollama:11434"}):
            settings = runpy.run_path(str(CONFIG_FILE))
        self.assertEqual(settings["OLLAMA_HOST"], "http://ollama:11434")


if __name__ == "__main__":
    unittest.main()
