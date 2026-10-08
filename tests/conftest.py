import os

import pytest


@pytest.fixture(autouse=True)
def isolated_environment():
    """coursekit loads .env files into os.environ: restore it after every test."""
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)
