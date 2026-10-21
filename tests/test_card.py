import unittest

from opensquilla_lark_streaming.card import (
    MAX_PANEL_ELEMENTS,
    build_card,
    footer_text,
    panel_title,
    round_elements,
)


def sample_rounds(count: int = 2, tools_per_round: int = 2) -> list[dict]:
    rounds = []
    for index in range(count):
        rounds.append(
            {
                "n": index + 1,
                "started": 0.0,
                "ended": 1.0,
                "text": "先确认要查什么，再决定用哪个工具。",
                "tools": [
                    {
                        "name": "bash",
                        "ok": True,
                        "elapsed": 0.201,
                        "detail": "git status --short",
                    }
                    for _ in range(tools_per_round)
                ],
            }
        )
    return rounds


class PanelTests(unittest.TestCase):
    def test_panel_title(self):
        self.assertEqual(
            panel_title(53, 9, 609),
            "🧠 9 轮 · 🛠️ 53 个工具 · ⏳ 10 分 9 秒",
        )

    def test_round_rows_include_title_preview_and_detail(self):
        rows = round_elements(sample_rounds(1, 1), now=1.0)
        contents = [row.get("text", {}).get("content", "") for row in rows]
        self.assertIn("<font color='green'>**第 1 轮 · 1.0s**</font>", contents[0])
        self.assertIn("Run command (201 ms)", contents[2])
        self.assertEqual(contents[3], "git status --short")

    def test_running_tool_is_turquoise(self):
        rounds = [
            {
                "n": 1,
                "started": 0.0,
                "ended": None,
                "text": "",
                "tools": [{"name": "bash", "ok": None, "elapsed": None, "detail": ""}],
            }
        ]
        rows = round_elements(rounds, now=1.0)
        self.assertIn("turquoise", rows[1]["text"]["content"])

    def test_collapse_only_beyond_cap(self):
        rows = round_elements(sample_rounds(30, 3), now=1.0)
        self.assertEqual(len(rows), 141)
        self.assertIn("已折叠", rows[0]["text"]["content"])
        self.assertGreater(MAX_PANEL_ELEMENTS, 100)


class FooterTests(unittest.TestCase):
    def test_footer_matches_hermes_shape(self):
        text = footer_text(
            done=True,
            failed=False,
            model="10router/ag/gemini-3.8-flash-high",
            weather="☀️ 临平 20.6°C/14.3°C",
            hitokoto="「保持好奇」—— x",
            elapsed_s=251.4,
            usage={"input": 10_000_000, "output": 18_000, "reasoning": 4_400, "iterations": 63},
        )
        first_line = text.split("\n\n")[0]
        self.assertTrue(first_line.startswith("✅ 已完成 · 4m 11s · ⚕gemini-3.8-flash-high"))
        self.assertIn("输入 10.0M 输出 18.0K 思考 4.4K", first_line)
        self.assertIn("/1.0M (15%)", first_line)
        self.assertIn("☀️ 临平", text)
        self.assertIn("💬 「保持好奇」", text)

    def test_failed_footer(self):
        text = footer_text(done=False, failed=True, model="", weather="", hitokoto="")
        self.assertEqual(text, "⚠️ 已中止")

    def test_streaming_footer_has_status(self):
        text = footer_text(done=False, failed=False, model="m", weather="", hitokoto="", elapsed_s=3.2)
        self.assertTrue(text.startswith("💭 处理中 · 3.2s · ⚕m"))


class CardTests(unittest.TestCase):
    def test_card_structure(self):
        card = build_card(
            text="答案是 42。",
            done=True,
            rounds=sample_rounds(1, 1),
            tools=[{"name": "bash", "ok": True, "elapsed": 0.2, "detail": "ls"}],
            model="p/m",
            elapsed_s=10,
            weather="☀️",
            hitokoto="「x」",
        )
        self.assertEqual(card["schema"], "2.0")
        self.assertEqual(card["header"]["template"], "green")
        self.assertEqual(card["header"]["title"]["content"], "✅ 已完成")
        elements = card["body"]["elements"]
        self.assertEqual(elements[0]["element_id"], "content")
        self.assertEqual(elements[1]["element_id"], "agent_process_panel")
        self.assertFalse(elements[1]["expanded"])
        self.assertEqual(elements[2]["tag"], "hr")
        self.assertIn("✅ 已完成", elements[3]["content"])
        self.assertFalse(card["config"]["streaming_mode"])

    def test_streaming_card_is_blue(self):
        card = build_card(text="partial", done=False, agent_name="Tanuki")
        self.assertEqual(card["header"]["template"], "blue")
        self.assertEqual(card["header"]["title"]["content"], "💭 Tanuki 处理中...")
        self.assertTrue(card["config"]["streaming_mode"])
        self.assertEqual(len(card["body"]["elements"]), 3)

    def test_long_body_truncated(self):
        card = build_card(text="x" * 30_000, done=True)
        content = card["body"]["elements"][0]["content"]
        self.assertLess(len(content), 18_200)
        self.assertIn("已截断", content)


if __name__ == "__main__":
    unittest.main()
