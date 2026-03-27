from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("lola-ai")
except PackageNotFoundError:
    __version__ = "unknown"
