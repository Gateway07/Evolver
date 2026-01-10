import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from evolver.export_schemas import export_model_schema
from evolver.level0 import L1OutputEnvelope


class TestDslModels(unittest.TestCase):
    def test_can_generate_json_schema(self) -> None:
        schema = L1OutputEnvelope.model_json_schema()
        self.assertIsInstance(schema, dict)
        self.assertEqual(schema.get("title"), "L1OutputEnvelope")

    def test_can_export_schema_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "l1_output.schema.json"
            written = export_model_schema(
                model=L1OutputEnvelope,
                output_file=output_file,
                overwrite=False,
            )

            self.assertTrue(written.exists())
            self.assertGreater(written.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
