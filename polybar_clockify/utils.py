from datetime import timedelta, datetime

from polybar_clockify.settings import LOCAL_TIMEZONE


def deltatime_to_hours_minutes_seconds(delta):
    delta -= timedelta(microseconds=delta.microseconds)
    hours, remainder = divmod(delta.seconds + delta.days * 3600 * 24, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours}:{minutes:02}:{seconds:02}'


def print_flush(*args, **kwargs):
    print(*args, **kwargs, flush=True)


def get_now(get_microseconds=False):
    if get_microseconds:
        return datetime.now(LOCAL_TIMEZONE)
    return datetime.now(LOCAL_TIMEZONE).replace(microsecond=0)


def get_today():
    return get_now().replace(hour=0, minute=0, second=0, microsecond=0)


def get_week():
    now = get_today()
    return now - timedelta(days=now.weekday())


def get_month():
    return get_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def serialize_datetime(datetime_):
    return datetime_.strftime('%Y-%m-%dT%H:%M:%SZ')

