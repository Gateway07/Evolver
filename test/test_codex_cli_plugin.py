import json
import os
import shutil
import unittest

from plugins import codex_cli_plugin


class TestCodexCliPlugin(unittest.TestCase):
    def test_extract_prompt_placeholders(self) -> None:
        placeholders = codex_cli_plugin._extract_prompt_placeholders(
            "Hello {TRACING_HEADER} {tracingId} {MECH_MIN_TRACING_RUNS} and again {tracingId}."
        )
        self.assertEqual(
            placeholders,
            {"TRACING_HEADER", "tracingId", "MECH_MIN_TRACING_RUNS"},
        )

    def test_resolve_prompt_params_autogenerates_tracing_id(self) -> None:
        required = {"tracingId", "TRACING_HEADER"}
        config = {"codex_cli": {"prompt_params": {"TRACING_HEADER": "X-TRACING_MDC_KEY"}}}

        resolved = codex_cli_plugin._resolve_prompt_params(
            required_keys=required,
            config=config,
            runtime_params=None,
        )

        self.assertEqual(resolved["TRACING_HEADER"], "X-TRACING_MDC_KEY")
        self.assertIsInstance(resolved["tracingId"], str)
        self.assertNotEqual(resolved["tracingId"].strip(), "")

    def test_resolve_prompt_params_requires_values(self) -> None:
        required = {"MECH_MIN_TRACING_RUNS"}
        config = {"codex_cli": {"prompt_params": {}}}

        with self.assertRaises(ValueError):
            codex_cli_plugin._resolve_prompt_params(
                required_keys=required,
                config=config,
                runtime_params=None,
            )

    def test_append_prompt_params_suffix(self) -> None:
        prompt = "Use header {TRACING_HEADER} with id {tracingId}."
        required = {"TRACING_HEADER", "tracingId"}
        resolved = {"TRACING_HEADER": "X-TRACING_MDC_KEY", "tracingId": "abc"}

        final_text = codex_cli_plugin._append_prompt_params_suffix(
            prompt_text=prompt,
            required_keys=required,
            resolved_params=resolved,
        )

        self.assertIn("PROMPT_PARAMETERS", final_text)
        self.assertIn("TRACING_HEADER=X-TRACING_MDC_KEY", final_text)
        self.assertIn("tracingId=abc", final_text)

    def test_extract_final_json_text(self) -> None:
        if os.environ.get("EVOLVER_RUN_CODEX_INTEGRATION_TESTS") != "1":
            self.skipTest("Set EVOLVER_RUN_CODEX_INTEGRATION_TESTS=1 to run codex integration tests")

        if shutil.which("codex") is None:
            self.skipTest("'codex' executable not found on PATH")

        prompt = """
Analyze application code in 'android' project to understand the search process and find counterexamples.
Test them by using Tracing API based on declared policy. 
As result mandatory produce required final JSON object to follow L1 Output Contract."""

        extracted, code = codex_cli_plugin.run(prompt)
        print(extracted)

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(extracted), {"ok": True, "n": 1})


if __name__ == "__main__":
    unittest.main()
