from requests import get, post, patch, put

from polybar_clockify.settings import API_KEY, EMAIL, PASSWORD, BASE_URL, GLOBAL_BASE_URL

headers = {
    'X-Api-Key': API_KEY,
    'content-type': 'application/json',
}


def get_auth_token():
    return post(f'{GLOBAL_BASE_URL}/auth/token', json={'email': EMAIL, 'password': PASSWORD}).json()


def get_user():
    return get(f'{BASE_URL}/user', headers=headers).json()


def get_workspaces():
    return get(f'{BASE_URL}/workspaces', headers=headers).json()


def get_projects(workspace_id, params=None):
    return get(f'{BASE_URL}/workspaces/{workspace_id}/projects', params, headers=headers).json()


def get_time_entries(workspace_id, user_id, params=None):
    return get(f'{BASE_URL}/workspaces/{workspace_id}/user/{user_id}/time-entries', params, headers=headers).json()


def post_time_entry(workspace_id, json=None):
    return post(f'{BASE_URL}/workspaces/{workspace_id}/time-entries', json=json, headers=headers).json()


def put_time_entry(workspace_id, id_, json=None):
    return put(f'{BASE_URL}/workspaces/{workspace_id}/time-entries/{id_}', json=json, headers=headers).json()


def patch_time_entry(workspace_id, user_id, json=None):
    return patch(f'{BASE_URL}/workspaces/{workspace_id}/user/{user_id}/time-entries', json=json, headers=headers).json()
