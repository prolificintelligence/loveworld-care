"""LoveWorld Care — Production /v1 API Package."""

__all__ = ["Settings", "get_settings"]


def __getattr__(name):
    # Institutional deployments package their own configuration and must not
    # eagerly import the independent legacy Care runtime.
    if name in __all__:
        from .config import Settings, get_settings

        return {"Settings": Settings, "get_settings": get_settings}[name]
    raise AttributeError(name)
