import unittest
from modules.score_rules import score_rank, combo_status, JUDGEMENT_ROWS
from modules.score_recognition_presenter import score_rank as flex_rank, combo_status as flex_combo


class ScoreRuleTests(unittest.TestCase):
    def test_rank_boundaries(self):
        for score, expected in [(100.5,'sss+'),(100,'sss'),(99.5,'ss+'),(99,'ss'),(98,'s+'),(97,'s'),(94,'aaa'),(90,'aa'),(80,'a'),(75,'bbb'),(70,'bb'),(60,'b'),(50,'c'),(0,'d')]:
            with self.subTest(score=score):
                self.assertEqual(score_rank(score), expected)
                self.assertEqual(flex_rank(score), expected.replace('+','p'))
                if score:
                    self.assertNotEqual(score_rank(score-0.0001), expected)
        self.assertIsNone(score_rank(None))

    def test_combo_and_incomplete_rows(self):
        rows={row:dict(great=0,good=0,miss=0) for row in JUDGEMENT_ROWS}
        for field,score,expected in [(None,101,'ap+'),(None,100,'ap'),('great',99,'fc+'),('good',98,'fc'),('miss',97,None)]:
            if field: rows['tap'][field]=1
            self.assertEqual(combo_status(score,rows),expected)
            self.assertEqual(flex_combo(rows,score),expected.replace('+','p') if expected else 'dummy')
        del rows['break']
        self.assertIsNone(combo_status(100,rows))
        self.assertIsNone(flex_combo(rows,100))
