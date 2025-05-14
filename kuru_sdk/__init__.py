from .orderbook import Orderbook, TxOptions, MarketParams
from .margin import MarginAccount
from .client_order_executor import ClientOrderExecutor
from .types import OrderRequest
from .logging_config import configure_logging, get_logger

# Configure logging with default settings
configure_logging()

__version__ = "0.1.0"

__all__ = [
    'Orderbook',
    'TxOptions',
    'MarketParams',
    'MarginAccount',
    'ClientOrderExecutor',
    'OrderRequest',
    'get_logger',
]
