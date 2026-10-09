import os
import shutil

import pytest

from coursekit import i18n, store


@pytest.fixture(autouse=True)
def no_npm(monkeypatch):
    """The suite never installs anything: npm is not found for the store unless a test brings its own fake."""
    real = shutil.which
    monkeypatch.setattr(store.shutil, "which", lambda name, *args, **kwargs: None if name == "npm" else real(name, *args, **kwargs))


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path_factory):
    """coursekit loads .env files into os.environ: restore it after every test. Messages in English unless a test says otherwise."""
    saved = dict(os.environ)
    os.environ["COURSEKIT_LANG"] = "en"
    os.environ["COURSEKIT_HOME"] = str(tmp_path_factory.mktemp("coursekit-home"))  # never the real store of the machine
    i18n.use(None)
    yield
    i18n.use(None)
    os.environ.clear()
    os.environ.update(saved)
