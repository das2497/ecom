# -*- coding: utf-8 -*-
"""Entry point cPanel's "Setup Python App" (Passenger) loads.

Passenger expects a WSGI `application` callable. FastAPI/Starlette are
ASGI, so we wrap the ASGI app with a2wsgi's adapter. This file is the
first thing to get working on Orange hosting -- if this loads and
/health responds, the ASGI-on-Passenger risk is cleared.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from a2wsgi import ASGIMiddleware

from main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
