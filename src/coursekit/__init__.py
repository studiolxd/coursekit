"""coursekit: AI-assisted e-learning course production."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("slxd-coursekit")
except PackageNotFoundError:  # running from a source checkout without installing
    __version__ = "0.0.0"
