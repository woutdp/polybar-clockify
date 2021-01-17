from polybar_clockify.settings import API_KEY, EMAIL, PASSWORD, BASE_URL, GLOBAL_BASE_URL

HEADERS = {
    'X-Api-Key': API_KEY,
    'content-type': 'application/json',
}


async def get(session, url, params=None, headers=None):
    async with session.get(url, params=params, headers=headers) as response:
        return await response.json()


async def post(session, url, json=None, headers=None):
    async with session.post(url, json=json, headers=headers) as response:
        return await response.json()


async def put(session, url, json=None, headers=None):
    async with session.put(url, json=json, headers=headers) as response:
        return await response.json()


async def patch(session, url, json=None, headers=None):
    async with session.patch(url, json=json, headers=headers) as response:
        return await response.json()


async def get_auth_token(session):
    return await post(session, f'{GLOBAL_BASE_URL}/auth/token', json={'email': EMAIL, 'password': PASSWORD})


async def get_user(session):
    return await get(session, f'{BASE_URL}/user', headers=HEADERS)


async def get_workspaces(session):
    return await get(session, f'{BASE_URL}/workspaces', headers=HEADERS)


async def get_projects(session, workspace_id, params=None):
    return await get(session, f'{BASE_URL}/workspaces/{workspace_id}/projects', params, headers=HEADERS)


async def get_time_entries(session, workspace_id, user_id, params=None):
    return await get(session, f'{BASE_URL}/workspaces/{workspace_id}/user/{user_id}/time-entries', params,
                     headers=HEADERS)


async def post_time_entry(session, workspace_id, json=None):
    return await post(session, f'{BASE_URL}/workspaces/{workspace_id}/time-entries', json=json, headers=HEADERS)


async def put_time_entry(session, workspace_id, id_, json=None):
    return await put(session, f'{BASE_URL}/workspaces/{workspace_id}/time-entries/{id_}', json=json, headers=HEADERS)


async def patch_time_entry(session, workspace_id, user_id, json=None):
    return await patch(session, f'{BASE_URL}/workspaces/{workspace_id}/user/{user_id}/time-entries', json=json,
                 headers=HEADERS)
