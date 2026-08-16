from __future__ import annotations

import json
import unittest
from pathlib import Path


class PluginSchemaTests(unittest.TestCase):
    def test_schema_uses_astrbot_provider_selector(self) -> None:
        schema_path = Path(__file__).parents[1] / "_conf_schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertEqual(
            schema["astrbot_provider_id"]["_special"], "select_provider"
        )
        self.assertEqual(schema["astrbot_provider_id"]["default"], "")
        self.assertFalse(schema["show_advanced_settings"]["default"])

    def test_schema_only_uses_supported_astrbot_types(self) -> None:
        schema_path = Path(__file__).parents[1] / "_conf_schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        supported = {
            "int",
            "float",
            "bool",
            "string",
            "text",
            "list",
            "file",
            "object",
            "template_list",
            "dict",
        }

        self.assertTrue(schema)
        for name, item in schema.items():
            self.assertIn(item["type"], supported, name)
            self.assertIn("default", item, name)


if __name__ == "__main__":
    unittest.main()
