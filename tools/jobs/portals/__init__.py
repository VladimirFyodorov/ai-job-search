"""Portal plugin registry for hunter-v2 job scrapers."""

_REGISTRY: dict[str, object] = {}


def register(portal) -> None:
    _REGISTRY[portal.name] = portal


def list_portals() -> list[str]:
    return list(_REGISTRY.keys())


def get_portal(name: str):
    return _REGISTRY[name]


# Auto-register built-ins on import
from .jooble import JooblePortal  # noqa: E402
from .infostud import InfostudPortal  # noqa: E402
from ..linkedin import LinkedInScraper  # noqa: E402

register(JooblePortal())
register(LinkedInScraper())  # LinkedInScraper has .name = "LinkedIn" class attribute
register(InfostudPortal())
