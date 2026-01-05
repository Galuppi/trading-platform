from abc import ABC, abstractmethod

class Connector(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """Establish a connection to the trading platform or data provider."""
        pass

    def connection_check(self) -> bool:
        """Checks if the connection is still valid."""
        pass