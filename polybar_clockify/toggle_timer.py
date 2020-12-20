from datetime import datetime

import pickledb

from api import post_time_entry, patch_time_entry, get_time_entries
from poll import synchronize

db = pickledb.load('database.db', True)

user = db.get('user')
workspace = db.get('workspace')

now = datetime.utcnow().replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')

if db.get('active_time_entry'):
    db.rem('active_time_entry')
    patch_time_entry(workspace['id'], user['id'], {'end': now})
    synchronize()
else:
    time_entries = db.get('time_entries')
    last_entry = time_entries[0] if time_entries else get_time_entries(workspace['id'], user['id'])[0]
    active_time_entry = post_time_entry(workspace['id'], {
        'start': now,
        'billable': last_entry['billable'],
        'description': last_entry['description'],
        'projectId': last_entry['projectId'],
    })
    db.set('active_time_entry', active_time_entry)
    synchronize()
