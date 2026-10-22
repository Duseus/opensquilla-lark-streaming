import unittest
from opensquilla_lark_streaming.card import build_card

class InstantCardTests(unittest.TestCase):
    def test_placeholder_card_display(self):
        card = build_card(text='', done=False, agent_name='Tanuki')
        elements = card['body']['elements']
        self.assertEqual(elements[0]['element_id'], 'content')
        self.assertTrue(bool(elements[0]['content']))
        self.assertEqual(card['header']['template'], 'blue')
        self.assertIn('Tanuki', card['header']['title']['content'])

if __name__ == '__main__':
    unittest.main()
