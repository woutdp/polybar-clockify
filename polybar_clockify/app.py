import asyncio
from asyncio import sleep
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from random import choice
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from string import ascii_lowercase, digits
from typing import Dict

import isodate
import websockets
from aiohttp import ClientSession

from polybar_clockify.api import (get_user, get_workspaces, get_projects, get_time_entries, post_time_entry,
                                  patch_time_entry, get_auth_token)
from polybar_clockify.settings import EMAIL, UNIX_HOST, UNIX_PORT
from polybar_clockify.utils import deltatime_to_hours_minutes_seconds, print_flush

TIME_ENTRY_STARTED = 'TIME_ENTRY_STARTED'
TIME_ENTRY_STOPPED = 'TIME_ENTRY_STOPPED'
TIME_ENTRY_DELETED = 'TIME_ENTRY_DELETED'

COMMAND_TOGGLE_HIDE = 'TOGGLE_HIDE'
COMMAND_TOGGLE_TIMER = 'TOGGLE_TIMER'
COMMAND_NEXT_MODE = 'NEXT_MODE'
COMMAND_PREVIOUS_MODE = 'PREVIOUS_MODE'

loop = asyncio.get_event_loop()


class WebsocketStatus(Enum):
    UNINITIALIZED = 1
    OPEN = 2
    CLOSED = 3


class Modes(Enum):
    OVERVIEW_TODAY = 1
    OVERVIEW_MONTH = 2

    def next(self):
        next_ = self.value + 1
        if next_ > len(Modes):
            return Modes(1)
        return Modes(next_)

    def previous(self):
        previous = self.value - 1
        if previous < 1:
            return Modes(len(Modes))
        return Modes(previous)


class Clockify:
    def __init__(self):
        self.hidden = False
        self.mode = Modes.OVERVIEW_TODAY
        self.websocket_status = WebsocketStatus.UNINITIALIZED
        self.user = None
        self.workspace = None
        self.projects = None
        self.monthly_time_entries = []
        self.active_project = []

    async def initialize(self):
        async with ClientSession() as session:
            self.user = await get_user(session)
            self.workspace = (await get_workspaces(session))[0]
            self.projects = {project['id']: project for project in await get_projects(session, self.workspace['id'])}
            await self.sync()

    async def sync(self):
        month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
        workspace_id = self.workspace['id']
        user_id = self.user['id']

        async with ClientSession() as session:
            self.monthly_time_entries = await get_time_entries(session, workspace_id, user_id,
                                                               {'start': month, 'page-size': 200})
            self.active_project = self.projects[(await self.get_last_time_entry())['projectId']]

    async def get_last_time_entry(self) -> Dict:
        if self.monthly_time_entries:
            return self.monthly_time_entries[0]

        async with ClientSession() as session:
            return (await get_time_entries(session, self.workspace['id'], self.user['id']))[0]

    @property
    def today_time_entries(self):
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
        return [entry for entry in self.monthly_time_entries if entry['timeInterval']['start'] > today]

    @property
    def hourly_rate(self):
        return Decimal(self.active_project['hourlyRate']['amount']) / 100

    @property
    def currency(self):
        return self.active_project['hourlyRate']['currency']

    @property
    def money_earned(self):
        return Decimal(
            self.hourly_rate * Decimal(self.time_spent_working / timedelta(hours=1))
        ).quantize(Decimal('.01'))

    @property
    def time_spent_working(self):
        # Splits the time entries into finished entries and an active entry
        entries = self.today_time_entries if self.mode == Modes.OVERVIEW_TODAY else self.monthly_time_entries

        finished, active = [], []
        for entry in entries:
            (finished, active)[entry['timeInterval']['duration'] is None].append(entry)

        # Calculates the active time entry duration
        difference = timedelta(0)
        if active:
            start = datetime.strptime(active[0]['timeInterval']['start'], '%Y-%m-%dT%H:%M:%S%z')
            now = datetime.now(timezone.utc)
            difference = now - start

        # Calculates the finished time entries total, and adds the active entry to it
        return difference + sum(
            (
                isodate.parse_duration(entry['timeInterval']['duration'])
                for entry
                in finished
            ), start=timedelta(0)
        )

    async def toggle_timer(self):
        now = datetime.utcnow().replace(microsecond=0)
        now_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        last_entry = await self.get_last_time_entry()

        async with ClientSession() as session:
            if last_entry['timeInterval']['duration'] is None:
                time_entry = self.monthly_time_entries[0]
                start = datetime.strptime(time_entry['timeInterval']['start'], '%Y-%m-%dT%H:%M:%S%z')
                difference = now - start.replace(tzinfo=None)
                time_entry['timeInterval']['end'] = now
                time_entry['timeInterval']['duration'] = isodate.duration_isoformat(difference)

                await patch_time_entry(session, self.workspace['id'], self.user['id'], {'end': now_str})
            else:
                time_entry = deepcopy(last_entry)
                time_entry['timeInterval']['start'] = now_str
                time_entry['timeInterval']['end'] = None
                time_entry['timeInterval']['duration'] = None
                self.monthly_time_entries.insert(0, time_entry)

                await post_time_entry(session, self.workspace['id'], {
                    'start': now_str,
                    'billable': last_entry['billable'],
                    'description': last_entry['description'],
                    'projectId': last_entry['projectId'],
                })

    async def websocket_connect(self):
        async with ClientSession() as session:
            token = (await get_auth_token(session)).get('token')
        random_str = ''.join(choice(f'{ascii_lowercase}{digits}') for _ in range(8))

        async with websockets.connect(f'wss://stomp.clockify.me/clockify/{EMAIL}/{random_str}') as websocket:
            await websocket.send(token)
            self.websocket_status = WebsocketStatus.OPEN

            while True:
                try:
                    response = await websocket.recv()
                except Exception:
                    self.websocket_status = WebsocketStatus.CLOSED
                    loop.create_task(self.websocket_connect())  # Restart the connection
                    break

                if response in (TIME_ENTRY_STARTED, TIME_ENTRY_STOPPED, TIME_ENTRY_DELETED):
                    loop.create_task(self.sync())

    async def websocket_auto_reconnect(self):
        while True:
            await sleep(10)

            if self.websocket_status == WebsocketStatus.CLOSED:
                loop.create_task(self.websocket_connect())

    async def unix_socket_connect(self):
        s = socket(AF_INET, SOCK_STREAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        try:
            s.bind((UNIX_HOST, UNIX_PORT))
        except OSError:
            print_flush('Warning: Unix socket already in use - not binding')
            return

        s.listen()
        s.setblocking(False)

        while True:
            client, _ = await loop.sock_accept(s)

            message = await loop.sock_recv(client, 255)
            message = message.decode().rstrip()

            if message == COMMAND_TOGGLE_TIMER:
                await self.toggle_timer()
            elif message == COMMAND_TOGGLE_HIDE:
                self.hidden = not self.hidden
            elif message == COMMAND_NEXT_MODE:
                self.mode = self.mode.next()
            elif message == COMMAND_PREVIOUS_MODE:
                self.mode = self.mode.previous()
            else:
                print_flush('Unknown command')
                await loop.sock_sendall(client, b'Unknown command')

    async def output(self):
        while True:
            await sleep(0.1)

            if self.hidden:
                print_flush('%{F#555}<hidden>%{F-}')
                continue

            ws_closed = '(no connection) ' if self.websocket_status == WebsocketStatus.CLOSED else ''
            working_time = deltatime_to_hours_minutes_seconds(self.time_spent_working)
            print_flush(f'{ws_closed}{self.money_earned} {self.currency} - {working_time}')


def run():
    print_flush('Loading...')

    clockify = Clockify()
    loop.run_until_complete(clockify.initialize())
    loop.create_task(clockify.websocket_connect())
    loop.create_task(clockify.websocket_auto_reconnect())
    loop.create_task(clockify.unix_socket_connect())
    loop.run_until_complete(clockify.output())
    loop.run_forever()


if __name__ == '__main__':
    run()
