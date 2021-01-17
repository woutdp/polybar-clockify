from datetime import timedelta


def deltatime_to_hours_minutes_seconds(delta):
    delta -= timedelta(microseconds=delta.microseconds)
    hours, remainder = divmod(delta.seconds + delta.days * 3600 * 24, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours}:{minutes:02}:{seconds:02}'


def print_flush(*args, **kwargs):
    print(*args, **kwargs, flush=True)
