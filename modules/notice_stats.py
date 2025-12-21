"""
公告统计模块

提供阅读率、投票统计等功能
"""

from typing import Optional, Dict
from modules.config_loader import USERS
from modules.notice_manager import get_notice_by_id, get_all_notices


def calculate_notice_stats(notice_id: str) -> Optional[Dict]:
    """
    计算公告统计数据

    Args:
        notice_id: 公告ID

    Returns:
        {
            'total_users': int,           # 总用户数
            'read_count': int,             # 已阅读数
            'read_percentage': float,      # 阅读率百分比
            'support_count': int,          # 支持数
            'oppose_count': int,           # 反对数
            'vote_percentage': float,      # 投票参与率(已投票/已阅读)
            'no_vote_count': int          # 未投票数(已阅读但未投票)
        }
    """
    notice = get_notice_by_id(notice_id)
    if not notice:
        return None

    total_users = len(USERS)
    read_count = 0
    support_count = 0
    oppose_count = 0

    for user_id, user_data in USERS.items():
        interactions = user_data.get('notice_interactions', {})
        interaction = interactions.get(notice_id)

        if interaction:
            if interaction.get('read'):
                read_count += 1

            vote = interaction.get('vote')
            if vote == 'support':
                support_count += 1
            elif vote == 'oppose':
                oppose_count += 1

    total_votes = support_count + oppose_count
    no_vote_count = read_count - total_votes

    return {
        'total_users': total_users,
        'read_count': read_count,
        'read_percentage': round((read_count / total_users * 100) if total_users > 0 else 0, 2),
        'support_count': support_count,
        'oppose_count': oppose_count,
        'vote_percentage': round((total_votes / read_count * 100) if read_count > 0 else 0, 2),
        'no_vote_count': no_vote_count
    }


def get_all_notices_stats() -> Dict:
    """
    获取所有公告的统计数据

    Returns:
        字典,key为notice_id,value为统计数据
    """
    notices = get_all_notices(include_drafts=True)
    stats = {}

    for notice in notices:
        notice_id = notice['id']
        stats[notice_id] = calculate_notice_stats(notice_id)

    return stats
