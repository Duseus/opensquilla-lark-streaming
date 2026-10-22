import unittest
from opensquilla_lark_streaming.card import build_card

class InstantFlowTests(unittest.TestCase):
    def test_initial_card_shows_thinking(self):
        card = build_card(text="", done=False, agent_name="Tanuki")
        self.assertEqual(card["body"]["elements"][0]["content"], "💭 正在思考中...")
        self.assertEqual(card["header"]["template"], "blue")

    def test_finished_empty_card_shows_space(self):
        card = build_card(text="", done=True, agent_name="Tanuki")
        self.assertEqual(card["body"]["elements"][0]["content"], " ")
        self.assertEqual(card["header"]["template"], "green")

    def test_text_overrides_placeholder(self):
        card = build_card(text="Here is answer", done=False, agent_name="Tanuki")
        self.assertEqual(card["body"]["elements"][0]["content"], "Here is answer")

if __name__ == "__main__":
    unittest.main()
