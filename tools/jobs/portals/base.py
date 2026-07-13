from abc import ABC, abstractmethod


class BasePortal(ABC):
    name: str  # class attribute, must be set by subclass

    def __init__(self, location: str = "Belgrade"):
        self.location = location

    @abstractmethod
    def search(self, query: str) -> list[dict]:
        """Search for jobs. Returns list of dicts with keys: title, company, url, location, source."""
        ...
