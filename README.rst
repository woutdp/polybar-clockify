================
polybar-clockify
================
.. image:: https://badge.fury.io/py/polybar-clockify.svg
    :target: https://badge.fury.io/py/polybar-clockify

Control Clockify through Polybar.

Features:

- Displaying money earned and time worked
- Toggle timer
- Hide output for privacy


Installation
------------
::

    pip install polybar-clockify


Configuration
-------------
Create credentials file in ``~/.config/polybar/clockify/credentials.json`` and fill out your clockify credentials.
Your will have to create a `clockify API key <https://clockify.me/user/settings/>`_ to make the module work. ::

    {
      "api-key": "your-api-key",
      "email": "your-email",
      "password": "your-password"
    }


Create a polybar module inside your polybar config add it to your active modules. ::

    [module/clockify]
    type = custom/script
    tail = true
    exec = polybar-clockify
    click-left = echo 'TOGGLE_TIMER' | nc 127.0.0.1 30300
    click-right = echo 'TOGGLE_HIDE' | nc 127.0.0.1 30300


Development
-----------
This package uses `poetry <https://python-poetry.org/>`_

To run in the terminal ::

    # Execute in the root folder of the repository
    poetry run python -u ./polybar_clockify/app.py

    # Example for polybar config
    [module/clockify]
    type = custom/script
    tail = true
    exec = poetry run python -u /home/<your_user>/polybar-clockify/polybar_clockify/app.py


Contribution
------------
At the moment the functionality is pretty basic, but sufficient for my use case.
If you want to extend the functionality I'd be delighted to accept pull requests!