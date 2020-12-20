from datetime import datetime

from api import get_time_entries


def update_time_entries(db):
    time_entries = get_time_entries(
        db.get('workspace')['id'],
        db.get('user')['id'],
        {'start': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')}
    )
    db.set('time_entries', time_entries)
    return time_entries
