import json
import os
import tempfile
import unittest
from pathlib import Path


class EnterpriseDataRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_path = Path(self.tmpdir.name) / "enterprises.json"
        os.environ["ENTERPRISE_DATA_PATH"] = str(self.data_path)

        from app.config import get_settings

        get_settings.cache_clear()

    def tearDown(self):
        from app.config import get_settings

        get_settings.cache_clear()
        os.environ.pop("ENTERPRISE_DATA_PATH", None)
        self.tmpdir.cleanup()

    def _write_enterprises(self, names):
        rows = []
        for index, name in enumerate(names, start=1):
            rows.append(
                {
                    "id": index,
                    "city": "深圳",
                    "name": name,
                    "themes": ["数字化"],
                    "visit_experience": f"{name}参观体验",
                    "sharing_topics": "",
                    "core_value": "",
                    "knowledge_points": "",
                    "pain_points": "",
                }
            )
        self.data_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    def test_enterprise_json_is_reloaded_on_each_query(self):
        from app.enterprise_data import search_overview

        self._write_enterprises(["旧企业"])
        old_result = search_overview(keyword="旧企业")
        self.assertEqual(["旧企业"], [item["name"] for item in old_result])

        self._write_enterprises(["新企业"])
        new_result = search_overview(keyword="新企业")

        self.assertEqual(["新企业"], [item["name"] for item in new_result])


if __name__ == "__main__":
    unittest.main()
