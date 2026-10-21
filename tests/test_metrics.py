import unittest

from opensquilla_lark_streaming.descriptors import (
    describe_tool,
    format_duration_ms,
    humanize_tool_name,
    resolve_descriptor,
    tool_detail,
)
from opensquilla_lark_streaming.metrics import (
    compact_num,
    footer_elapsed,
    human_duration,
    resolve_context_window,
)


class DescriptorTests(unittest.TestCase):
    def test_command_title_with_duration(self):
        title, icon = describe_tool("bash", 201)
        self.assertEqual(title, "Run command (201 ms)")
        self.assertEqual(icon, "setting_outlined")

    def test_seconds_duration(self):
        title, _ = describe_tool("web_search", 1400)
        self.assertEqual(title, "Search (1.4 s)")

    def test_read_uses_basename(self):
        detail = tool_detail("read_file", {"file_path": "/home/user/app/config.yaml"})
        self.assertEqual(detail, "config.yaml")

    def test_command_detail_kept(self):
        detail = tool_detail("bash", {"command": "git status --short"})
        self.assertEqual(detail, "git status --short")

    def test_unknown_tool_humanized(self):
        self.assertEqual(humanize_tool_name("some_tool"), "Some tool")
        title, icon = describe_tool("some_tool", None)
        self.assertEqual(title, "Some tool")
        self.assertEqual(icon, "tool_02")

    def test_detail_newlines_collapsed(self):
        detail = tool_detail("bash", {"command": "line1\nline2"})
        self.assertEqual(detail, "line1 line2")

    def test_alias_with_suffix(self):
        self.assertIsNotNone(resolve_descriptor("web_search_plus"))

    def test_duration_formatting(self):
        self.assertEqual(format_duration_ms(0.4), "0 ms")
        self.assertEqual(format_duration_ms(999), "999 ms")
        self.assertEqual(format_duration_ms(1500), "1.5 s")


class MetricsTests(unittest.TestCase):
    def test_compact_num(self):
        self.assertEqual(compact_num(999), "999")
        self.assertEqual(compact_num(18_000), "18.0K")
        self.assertEqual(compact_num(10_000_000), "10.0M")

    def test_footer_elapsed(self):
        self.assertEqual(footer_elapsed(6.4), "6.4s")
        self.assertEqual(footer_elapsed(251), "4m 11s")

    def test_human_duration(self):
        self.assertEqual(human_duration(7.7), "7.7 秒")
        self.assertEqual(human_duration(609), "10 分 9 秒")

    def test_context_window_known_models(self):
        self.assertEqual(resolve_context_window("10router/ag/gemini-3.8-flash-high"), 1_048_576)
        self.assertGreaterEqual(resolve_context_window("gpt-5.5"), 400_000)
        self.assertGreater(resolve_context_window("totally-unknown-model"), 0)


if __name__ == "__main__":
    unittest.main()
