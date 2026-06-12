from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Collector(ABC):
    @abstractmethod
    async def collect(self) -> Any:
        raise NotImplementedError
