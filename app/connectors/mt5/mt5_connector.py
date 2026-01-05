import MetaTrader5 as mt5
import logging
from app.base.base_connector import Connector
from app.common.models.model_connector import ConnectorConfig

logger = logging.getLogger(__name__)

class Mt5Connector(Connector):
    def __init__(self, config: ConnectorConfig):
        if config.login is None or config.password is None:
            raise ValueError("MT5 requires 'login' and 'password' in ConnectorConfig.")

        self.config = config

    def connect(self) -> bool:
        """Establish connection to MetaTrader 5 with specific account credentials."""
        path= self.config.terminal_path
        login = int(self.config.login)
        password = self.config.password
        server = self.config.server
        timeout = 60000

        logger.info(f"Attempting to connect to MT5: Account {login}, Server: {server}")

        if not mt5.initialize(
            path=path,
            login=login,
            password=password,
            server=server,
            timeout=timeout
        ):
            logger.error(f"MT5 initialize() failed: {mt5.last_error()}")
            return False

        account_info = mt5.account_info()
        if account_info is None:
            logger.error(f"Failed to retrieve account info after login: {mt5.last_error()}")
            mt5.shutdown()
            return False

        if account_info.login != login:
            logger.warning(f"Connected but logged into different account: {account_info.login} (expected {login})")

        logger.info(
            f"Successfully connected to MT5!\n"
            f"   Account: #{account_info.login} ({account_info.name})\n"
            f"   Balance: {account_info.balance} {account_info.currency}\n"
            f"   Server: {account_info.server}\n"
            f"   Terminal Path: {path}"
        )
        
        return True