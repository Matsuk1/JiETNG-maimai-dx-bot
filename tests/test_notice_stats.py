import unittest
from modules.notice_stats import summarize_notices


class NoticeStatsTests(unittest.TestCase):
    def test_multiple_notices_single_snapshot(self):
        users={'a':{'notice_interactions':{'n1':{'read':True,'vote':'support'},'n2':{'read':True}}},
               'b':{'notice_interactions':{'n1':{'read':True,'vote':'oppose'},'deleted':{'read':True}}},
               'c':{}}
        result=summarize_notices(['n1','n2','n3'], users)
        self.assertEqual(result['n1'],dict(total_users=3,read_count=2,support_count=1,oppose_count=1,read_percentage=66.67,vote_percentage=100.0,no_vote_count=0))
        self.assertEqual(result['n2']['no_vote_count'],1)
        self.assertEqual(result['n3']['read_percentage'],0)
        self.assertEqual(summarize_notices(['n'],{})['n']['vote_percentage'],0)
