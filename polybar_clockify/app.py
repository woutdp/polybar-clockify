import asyncio
import sys
from asyncio import sleep
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from random import choice
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from string import ascii_lowercase, digits
from typing import Dict

import isodate
import websockets

from polybar_clockify.api import (get_auth_token, get_user, get_workspaces, get_projects, get_time_entries,
                                  patch_time_entry, post_time_entry)
from polybar_clockify.settings import EMAIL, UNIX_HOST, UNIX_PORT

TIME_ENTRY_STARTED = 'TIME_ENTRY_STARTED'
TIME_ENTRY_STOPPED = 'TIME_ENTRY_STOPPED'
TIME_ENTRY_DELETED = 'TIME_ENTRY_DELETED'

COMMAND_TOGGLE_HIDE = 'TOGGLE_HIDE'
COMMAND_TOGGLE_TIMER = 'TOGGLE_TIMER'


class WebsocketStatus(Enum):
    UNINITIALIZED = 1
    OPEN = 2
    CLOSED = 3


class Clockify:
    def __init__(self):
        self.hidden = False
        self.websocket_status = WebsocketStatus.UNINITIALIZED
        self.user = get_user()
        self.workspace = get_workspaces()[0]
        self.projects = {project['id']: project for project in get_projects(self.workspace['id'])}
        self.today_time_entries = []
        self.all_time_entries = get_time_entries(self.workspace['id'], self.user['id'])
        self.active_project = []
        self.sync()

    def sync(self):
        self.today_time_entries = get_time_entries(
            self.workspace['id'],
            self.user['id'],
            {'start': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')}
        )
        self.active_project = self.projects[self.today_time_entries[0]['projectId']]

    @property
    def hourly_rate(self):
        return Decimal(self.active_project['hourlyRate']['amount']) / 100

    @property
    def currency(self):
        return self.active_project['hourlyRate']['currency']

    @property
    def money_earned(self):
        return Decimal(
            self.hourly_rate * Decimal(self.time_spent_working_today / timedelta(hours=1))
        ).quantize(Decimal('.01'))

    @property
    def time_spent_working_today(self):
        # Splits the time entries into finished entries and an active entry
        finished, active = [], []
        for entry in self.today_time_entries:
            (finished, active)[entry['timeInterval']['duration'] is None].append(entry)

        # Calculates the active time entry duration
        difference = timedelta(0)
        if active:
            start = datetime.strptime(active[0]['timeInterval']['start'], '%Y-%m-%dT%H:%M:%S%z')
            now = datetime.now(timezone.utc).replace(microsecond=0)
            difference = now - start

        # Calculates the finished time entries total, and adds the active entry to it
        return difference + sum(
            (
                isodate.parse_duration(entry['timeInterval']['duration'])
                for entry
                in finished
            ), start=timedelta(0)
        )

    def get_last_time_entry(self) -> Dict:
        if self.today_time_entries:
            return self.today_time_entries[0]
        return get_time_entries(self.workspace['id'], self.user['id'])[0]

    async def toggle_timer(self):
        now = datetime.utcnow().replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
        last_entry = self.get_last_time_entry()

        if last_entry['timeInterval']['duration'] is None:
            patch_time_entry(self.workspace['id'], self.user['id'], {'end': now})
        else:
            post_time_entry(self.workspace['id'], {
                'start': now,
                'billable': last_entry['billable'],
                'description': last_entry['description'],
                'projectId': last_entry['projectId'],
            })

    async def output(self):
        while True:
            await sleep(0.1)

            if self.hidden:
                print_flush('%{F#555}<hidden>%{F-}')
                continue

            if self.websocket_status == WebsocketStatus.CLOSED:
                print_flush('WEBSOCKET CONNECTION CLOSED')
                continue

            print_flush(f'{self.money_earned} {self.currency} - {self.time_spent_working_today}')

    async def websocket_connect(self):
        token = get_auth_token().get('token')
        random_str = ''.join(choice(f'{ascii_lowercase}{digits}') for _ in range(8))

        async with websockets.connect(f'wss://stomp.clockify.me/clockify/{EMAIL}/{random_str}') as websocket:
            await websocket.send(token)
            self.websocket_status = WebsocketStatus.OPEN

            while True:
                try:
                    response = await websocket.recv()
                except websockets.ConnectionClosed:
                    self.websocket_status = False
                    break

                if response == TIME_ENTRY_STARTED:
                    self.sync()
                elif response == TIME_ENTRY_STOPPED:
                    self.sync()
                elif response == TIME_ENTRY_DELETED:
                    self.sync()

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

        loop = asyncio.get_event_loop()

        while True:
            client, _ = await loop.sock_accept(s)

            message = await loop.sock_recv(client, 255)
            message = message.decode().rstrip()

            if message == COMMAND_TOGGLE_TIMER:
                await self.toggle_timer()
            elif message == COMMAND_TOGGLE_HIDE:
                self.hidden = not self.hidden
            else:
                print('Unknown command')
                await loop.sock_sendall(client, b'Unknown command')


def print_flush(*args, **kwargs):
    print(*args, **kwargs, flush=True)


def run():
    print_flush('Loading...')

    clockify = Clockify()
    loop = asyncio.get_event_loop()
    loop.create_task(clockify.websocket_connect())
    loop.create_task(clockify.unix_socket_connect())
    loop.run_until_complete(clockify.output())
    loop.run_forever()


if __name__ == '__main__':
    run()
