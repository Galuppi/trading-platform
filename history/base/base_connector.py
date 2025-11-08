'''"""This module defines classes related to Connector."""'''
from abc import ABC, abstractmethod

class Connector(ABC):

    @abstractmethod
    def connect(self: Any) -> bool:
        """Establish a connection to the trading platform or data provider."""
        pass
