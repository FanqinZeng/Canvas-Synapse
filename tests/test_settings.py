import json
import os
import tempfile
import unittest
from pathlib import Path

from synapse.settings import Settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = Settings(self.tmp.name)

    def test_secrets_masked_preserved_and_explicitly_clearable(self):
        public = self.settings.update({"api_key": "secret-key", "canvas_token": "private-token"})
        self.assertNotIn("secret-key", json.dumps(public))
        self.assertNotIn("api_key", public)
        self.assertTrue(public["api_key_set"])
        self.settings.update({"api_key": "", "canvas_token": ""})
        self.assertEqual(self.settings.get()["api_key"], "secret-key")
        self.settings.update({"clear_api_key": True})
        self.assertFalse(self.settings.public()["api_key_set"])

    def test_private_file_and_restart(self):
        self.settings.update({"model": "chosen-model"})
        self.assertEqual(Settings(self.tmp.name).get()["model"], "chosen-model")
        if os.name != "nt":
            self.assertEqual(self.settings.path.stat().st_mode & 0o777, 0o600)

    def test_reject_unsafe_urls_and_invalid_budgets(self):
        for change in [{"api_base": "http://evil.example/api"}, {"api_base": "https://user:pass@example.com"},
                       {"canvas_base": "https://attacker.example"}, {"context_chars": True}, {"context_chars": 1}]:
            with self.assertRaises(ValueError):
                self.settings.update(change)
        self.settings.update({"api_base": "http://127.0.0.1:11434/v1"})

    def test_change_provider_origin_does_not_leak_old_key(self):
        self.settings.update({"api_key": "old-provider-key"})
        self.settings.update({"api_base": "https://different.example/v1", "api_key": ""})
        self.assertEqual(self.settings.get()["api_key"], "")
        self.settings.update({"api_base": "https://new.example/v1", "api_key": "new-provider-key"})
        self.assertEqual(self.settings.get()["api_key"], "new-provider-key")

    def test_reject_header_control_characters(self):
        for value in ("secret\nHeader:value", "不是API密钥", "secret value"):
            with self.assertRaises(ValueError):
                self.settings.update({"api_key": value})


if __name__ == "__main__":
    unittest.main()
