import unittest
from opensquilla_lark_streaming.theme import get_theme, is_emoji_icon

class ThemeTests(unittest.TestCase):
    def test_theme_keys(self):
        theme = get_theme()
        self.assertIn('tool_icons', theme)
        self.assertIn('exec', theme['tool_icons'])
        self.assertTrue(is_emoji_icon(theme['tool_icons']['exec']))
        self.assertEqual(theme['round_icon'], '🌊')

if __name__ == '__main__':
    unittest.main()
