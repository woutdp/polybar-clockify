import asyncio
from asyncio import sleep
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import isodate as isodate
import pickledb

from api import get_user, get_workspaces, get_projects
from db import update_time_entries

db = pickledb.load('database.db', True)


def calculate_money_earned(entry, duration):
    db.load('database.db', True)
    hourly_rate = Decimal(db.get('projects')[entry['projectId']]['hourlyRate']['amount']) / 100
    return hourly_rate * Decimal(duration / timedelta(hours=1))


async def full_synchronize():
    db.set('user', get_user())
    db.set('workspace', get_workspaces()[0])
    db.set('projects', {project['id']: project for project in get_projects(db.get('workspace')['id'])})

    synchronize()


def synchronize():
    db.load('database.db', True)
    time_entries = update_time_entries(db)

    total = timedelta(0)
    money_earned = 0
    active_time_entry = None

    for entry in time_entries:
        duration = entry['timeInterval']['duration']
        if duration:
            duration = isodate.parse_duration(entry['timeInterval']['duration'])
            money_earned += calculate_money_earned(entry, duration)
            total += duration
        else:
            active_time_entry = entry

    db.set('active_time_entry', active_time_entry)
    db.set('total', total.total_seconds())
    db.set('money_earned', str(money_earned))


async def main():
    await full_synchronize()
    synchronize()


async def output():
    while True:
        db.load('database.db', True)
        active_time_entry = db.get('active_time_entry')
        total = timedelta(seconds=db.get('total'))
        if active_time_entry:
            start = datetime.strptime(active_time_entry['timeInterval']['start'], '%Y-%m-%dT%H:%M:%S%z')
            now = datetime.now(timezone.utc).replace(microsecond=0)
            difference = now - start
            money_earned = calculate_money_earned(active_time_entry, difference)
            print(f"{Decimal(db.get('money_earned')) + money_earned:.2f} CAD - {total + difference}")
        else:
            print(f"{Decimal(db.get('money_earned')):.2f} CAD - {total}")

        await sleep(1)


async def periodic_sync():
    while True:
        await sleep(60)
        synchronize()


async def periodic_full_sync():
    while True:
        await sleep(3600)
        await full_synchronize()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.create_task(output())
    loop.create_task(periodic_sync())
    loop.run_forever()
