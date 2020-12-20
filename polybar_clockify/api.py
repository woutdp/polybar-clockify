import json
import os

from requests import get, post, patch, put

with open(f'{os.getcwd()}/credentials.json') as file:
    api_key = json.load(file)['clockify_api_key']

base_url = 'https://api.clockify.me/api/v1'
headers = {
    'X-Api-Key': api_key,
    'content-type': 'application/json',
}


def get_user():
    return get(f'{base_url}/user', headers=headers).json()


def get_workspaces():
    return get(f'{base_url}/workspaces', headers=headers).json()


def get_projects(workspace_id, params=None):
    return get(f'{base_url}/workspaces/{workspace_id}/projects', params, headers=headers).json()


def get_time_entries(workspace_id, user_id, params=None):
    return get(f'{base_url}/workspaces/{workspace_id}/user/{user_id}/time-entries', params, headers=headers).json()


def post_time_entry(workspace_id, json=None):
    return post(f'{base_url}/workspaces/{workspace_id}/time-entries', json=json, headers=headers).json()


def put_time_entry(workspace_id, id_, json=None):
    return put(f'{base_url}/workspaces/{workspace_id}/time-entries/{id_}', json=json, headers=headers).json()


def patch_time_entry(workspace_id, user_id, json=None):
    return patch(f'{base_url}/workspaces/{workspace_id}/user/{user_id}/time-entries', json=json, headers=headers).json()
