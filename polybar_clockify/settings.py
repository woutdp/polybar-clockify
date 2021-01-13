import json
from pathlib import Path

with open(f'{Path.home()}/.config/polybar/clockify/credentials.json') as credentials:
    json = json.load(credentials)
    API_KEY = json.get('api-key')
    EMAIL = json.get('email')
    PASSWORD = json.get('password')

BASE_URL = 'https://api.clockify.me/api/v1'
GLOBAL_BASE_URL = 'https://global.api.clockify.me'

UNIX_HOST = '127.0.0.1'
UNIX_PORT = 30300
