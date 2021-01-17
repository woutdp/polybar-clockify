import asyncio
from asyncio import sleep
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from random import choice
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from string import ascii_lowercase, digits
from typing import Optional, List, Dict

import pytz
import websockets
from aiohttp import ClientSession

from polybar_clockify.api import (get_user, get_workspaces, get_projects, get_time_entries, post_time_entry,
                                  patch_time_entry, get_auth_token)
from polybar_clockify.objects import TimeEntry, Project, Workspace, User
from polybar_clockify.settings import EMAIL, UNIX_HOST, UNIX_PORT
from polybar_clockify.utils import deltatime_to_hours_minutes_seconds, print_flush, get_now, get_today, get_month, \
    serialize_datetime, get_week

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
    OVERVIEW_WEEK = 2
    OVERVIEW_MONTH = 3

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
        self.user: Optional[User] = None
        self.workspace: Optional[Workspace] = None
        self.projects: Dict = {}
        self.monthly_time_entries: List[TimeEntry] = []
        self.active_project: Optional[Project] = None

    async def initialize(self):
        async with ClientSession() as session:
            self.user = await get_user(session)
            self.workspace = (await get_workspaces(session))[0]
            self.projects = {project.id: project for project in await get_projects(session, self.workspace.id)}
            await self.sync()

    async def sync(self):
        async with ClientSession() as session:
            self.monthly_time_entries = await get_time_entries(
                session,
                self.workspace.id,
                self.user.id,
                {
                    'start': serialize_datetime(get_month()),
                    'page-size': 200
                }
            )
            self.active_project = self.projects[(await self.get_last_time_entry()).project_id]

    async def get_last_time_entry(self) -> TimeEntry:
        if self.monthly_time_entries:
            return self.monthly_time_entries[0]

        async with ClientSession() as session:
            return (await get_time_entries(session, self.workspace.id, self.user.id))[0]

    @property
    def today_time_entries(self):
        return [entry for entry in self.monthly_time_entries if entry.time_interval.start > get_today()]

    @property
    def weekly_time_entries(self):
        return [entry for entry in self.monthly_time_entries if entry.time_interval.start > get_week()]

    @property
    def hourly_rate(self):
        return Decimal(self.active_project.hourly_rate.amount) / 100

    @property
    def currency(self):
        return self.active_project.hourly_rate.currency

    @property
    def amount_earned(self):
        return Decimal(
            self.hourly_rate * Decimal(self.time_spent_working / timedelta(hours=1))
        ).quantize(Decimal('.01'))

    @property
    def time_spent_working(self):
        if self.mode == Modes.OVERVIEW_TODAY:
            time_entries = self.today_time_entries
        elif self.mode == Modes.OVERVIEW_WEEK:
            time_entries = self.weekly_time_entries
        else:
            time_entries = self.monthly_time_entries

        finished, active = [], []
        for entry in time_entries:
            (finished, active)[entry.time_interval.duration is None].append(entry)

        finished_total = sum((entry.time_interval.duration for entry in finished), start=timedelta(0))
        active_total = timedelta(0)
        if active:
            active_total = get_now(get_microseconds=True) - active[0].time_interval.start

        return finished_total + active_total

    async def toggle_timer(self):
        now = datetime.now(pytz.utc).replace(microsecond=0)
        now_str = serialize_datetime(now)
        last_entry = await self.get_last_time_entry()

        async with ClientSession() as session:
            if last_entry.time_interval.duration is None:
                # We predict the time entry that will be set by clockify, this way we get instant feedback on clicking
                time_entry = self.monthly_time_entries[0]
                time_entry.time_interval.end = now
                time_entry.time_interval.duration = now - time_entry.time_interval.start

                await patch_time_entry(session, time_entry.workspace_id, time_entry.user_id, {'end': now_str})
            else:
                # We predict the time entry that will be set by clockify, this way we get instant feedback on clicking
                time_entry = deepcopy(last_entry)
                time_entry.time_interval.start = now
                time_entry.time_interval.end = None
                time_entry.time_interval.duration = None
                self.monthly_time_entries.insert(0, time_entry)

                await post_time_entry(session, time_entry.workspace_id, {
                    'start': now_str,
                    'billable': last_entry.billable,
                    'description': last_entry.description,
                    'projectId': last_entry.project_id,
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
            print_flush(f'{ws_closed}{self.amount_earned} {self.currency} - {working_time}')


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
