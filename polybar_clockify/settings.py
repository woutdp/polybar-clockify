import os
import json

with open(f'{os.getcwd()}/credentials.json') as file:
    json = json.load(file)
    API_KEY = json.get('api-key')
    EMAIL = json.get('email')
    PASSWORD = json.get('password')

BASE_URL = 'https://api.clockify.me/api/v1'
GLOBAL_BASE_URL = 'https://global.api.clockify.me'

UNIX_HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
UNIX_PORT = 30300  # Port to listen on (non-privileged ports are > 1023)
