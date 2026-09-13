"""Aggregate notice interactions from one consistent user snapshot."""


def summarize_notices(notice_ids, users):
    totals = {notice_id: {'read_count': 0, 'support_count': 0, 'oppose_count': 0}
              for notice_id in notice_ids}
    for user in users.values():
        for notice_id, interaction in user.get('notice_interactions', {}).items():
            counts = totals.get(notice_id)
            if counts is None or not interaction:
                continue
            counts['read_count'] += bool(interaction.get('read'))
            vote = interaction.get('vote')
            if vote in ('support', 'oppose'):
                counts[f'{vote}_count'] += 1
    total_users = len(users)
    for counts in totals.values():
        reads = counts['read_count']
        votes = counts['support_count'] + counts['oppose_count']
        counts.update(
            total_users=total_users,
            read_percentage=round(reads / total_users * 100, 2) if total_users else 0,
            vote_percentage=round(votes / reads * 100, 2) if reads else 0,
            no_vote_count=reads - votes,
        )
    return totals


def calculate_notice_stats(notice_id):
    from modules.notice_manager import get_notice_by_id
    from modules.user_db import load_all_users

    if not get_notice_by_id(notice_id):
        return None
    return summarize_notices([notice_id], load_all_users())[notice_id]


def get_all_notices_stats():
    from modules.notice_manager import get_all_notices
    from modules.user_db import load_all_users

    notices = get_all_notices(include_drafts=True)
    if not notices:
        return {}
    return summarize_notices((notice['id'] for notice in notices), load_all_users())
