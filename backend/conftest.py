"""
Root conftest for backend tests.
Delegates to app.tests.conftest to enforce database isolation.
"""
from app.tests.conftest import *
