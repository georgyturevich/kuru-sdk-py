import datetime
from typing import Optional, List, Literal
from dataclasses import dataclass

@dataclass
class MarketParams:
    price_precision: int
    size_precision: int
    base_asset: str
    base_asset_decimals: int
    quote_asset: str
    quote_asset_decimals: int
    tick_size: int
    min_size: int
    max_size: int
    taker_fee_bps: int
    maker_fee_bps: int

@dataclass
class TxOptions:
    gas_limit: Optional[int] = None
    gas_price: Optional[int] = None  # Used as maxFeePerGas
    max_priority_fee_per_gas: Optional[int] = None
    nonce: Optional[int] = None

@dataclass
class VaultParams:
    kuru_amm_vault: str
    vault_best_bid: int
    bid_partially_filled_size: int
    vault_best_ask: int
    ask_partially_filled_size: int
    vault_bid_order_size: int
    vault_ask_order_size: int
    spread: int

@dataclass
class OrderPriceSize:
    price: float
    size: float

@dataclass
class OrderCreatedEvent:
    order_id: int
    price: str
    size: str
    is_buy: bool

@dataclass
class OrderCreatedPayload:
    order_id: int
    market_address: str
    owner: str
    price: str
    size: str
    is_buy: bool
    block_number: int
    tx_index: int
    log_index: int
    transaction_hash: str
    trigger_time: str
    remaining_size: str
    is_canceled: bool
    
@dataclass
class TradePayload:
    order_id: int
    market_address: str
    maker_address: str
    is_buy: bool
    price: str
    updated_size: str
    taker_address: str
    filled_size: str
    block_number: int
    tx_index: int
    log_index: int
    transaction_hash: str
    trigger_time: str

@dataclass
class OrderCancelledPayload:
    order_ids: List[int]
    maker_address: str
    canceled_orders_data: List[OrderCreatedPayload]
@dataclass
class OrderRequest:
    market_address: str # Market address
    order_type: Literal["limit", "market", "cancel"] # Order type
    cloid: Optional[str] = None # Client order id for internal reference
    side: Optional[Literal["buy", "sell"]] = None # optional for cancel orders
    price: Optional[str] = None  # Optional for market orders
    size: Optional[str] = None # optional for cancel orders
    post_only: Optional[bool] = False # Post only for limit orders
    is_margin: Optional[bool] = True # Use funds from margin account
    fill_or_kill: Optional[bool] = False # Fill or kill for market orders
    min_amount_out: Optional[str] = None  # For market orders only
    cancel_order_ids: Optional[List[int | str]] = None # For batch cancel
    cancel_cloids: Optional[List[str]] = None # For batch cancel
    tick_normalization: Optional[Literal["round_up", "round_down"]] = "round_down" # rounds up or down to the nearest tick size

@dataclass
class Order:
    market_address: str
    order_id: int
    owner: str
    size: str
    price: str
    is_buy: bool
    remaining_size: str
    is_canceled: bool
    block_number: str
    tx_index: str
    log_index: str
    transaction_hash: str
    trigger_time: datetime
    total_size: str

@dataclass
class L2Book:
    block_num: int
    buy_orders: List[OrderPriceSize]
    sell_orders: List[OrderPriceSize]
    amm_buy_orders: List[OrderPriceSize]
    amm_sell_orders: List[OrderPriceSize]
    vault_params: VaultParams

    def __str__(self) -> str:
        # Combine regular and AMM orders
        combined_buys = {}
        combined_sells = {}

        # Process regular orders
        for order in self.buy_orders:
            combined_buys[order.price] = order.size
        for order in self.sell_orders:
            combined_sells[order.price] = order.size

        # # Add AMM orders, combining sizes for matching prices
        for order in self.amm_buy_orders:
            combined_buys[order.price] = combined_buys.get(order.price, 0) + order.size
        for order in self.amm_sell_orders:
            combined_sells[order.price] = combined_sells.get(order.price, 0) + order.size

        # Convert to sorted lists (sells in descending order)
        sorted_buys = sorted(combined_buys.items(), key=lambda x: x[0], reverse=True)[:10]  # Top 10 bids
        sorted_sells = sorted(combined_sells.items(), key=lambda x: x[0], reverse=True)[-10:]  # Last 10 asks

        # Format the table
        header = f"{'Price':>12} | {'Size':>12}"
        separator = "-" * 27
        rows = []

        # Add sell orders (highest to lowest)
        for price, size in sorted_sells:
            rows.append(f"{price:>12.8f} | {size:>12.8f}")

        # Add separator between sells and buys
        rows.append(separator)

        # Add buy orders (highest to lowest)
        for price, size in sorted_buys:
            rows.append(f"{price:>12.8f} | {size:>12.8f}")

        # Combine all parts
        return f"Block: {self.block_num}\n{header}\n{separator}\n" + "\n".join(rows)
    
    def to_formatted_l2_book(self) -> 'FormattedL2Book':
        # combine the orderbook and amm orderbook similar to the __str__ method
        combined_buys = {}
        combined_sells = {}

        for order in self.buy_orders:
            combined_buys[order.price] = order.size
        for order in self.sell_orders:
            combined_sells[order.price] = order.size

        # Not adding AMM orders to 
        for order in self.amm_buy_orders:
            combined_buys[order.price] = combined_buys.get(order.price, 0) + order.size
        for order in self.amm_sell_orders:
            combined_sells[order.price] = combined_sells.get(order.price, 0) + order.size
        
        return FormattedL2Book(
            block_num=self.block_num,
            buy_orders=combined_buys,
            sell_orders=combined_sells
        )

@dataclass
class FormattedL2Book:
    block_num: int
    buy_orders: List[OrderPriceSize]
    sell_orders: List[OrderPriceSize]

    def __str__(self) -> str:
        # Format the table
        header = f"{'Price':>12} | {'Size':>12}"
        separator = "-" * 27
        rows = []

        # Add sell orders (highest to lowest)
        for order in sorted(self.sell_orders, key=lambda x: x.price):
            rows.append(f"{order.price:>12.8f} | {order.size:>12.8f}")

        # Add separator between sells and buys
        rows.append(separator)

        # Add buy orders (highest to lowest)
        for order in sorted(self.buy_orders, key=lambda x: x.price, reverse=True):
            rows.append(f"{order.price:>12.8f} | {order.size:>12.8f}")

        # Combine all parts
        return f"Block: {self.block_num}\n{header}\n{separator}\n" + "\n".join(rows)

@dataclass
class Pagination:
    total: int
    page: int
    pageSize: int

@dataclass
class OrderResponseData:
    data: List[Order]
    pagination: Pagination

@dataclass
class OrderResponse:
    success: bool
    code: int
    timestamp: int
    data: OrderResponseData

@dataclass
class Trade:
    orderid: int
    makeraddress: str
    takeraddress: str
    isbuy: bool
    price: str
    filledsize: str
    blocknumber: str
    txindex: str
    logindex: str
    transactionhash: str
    triggertime: datetime
    monadPrice: float

@dataclass
class TradeResponseData:
    data: List[Trade]
    pagination: Pagination
    
@dataclass
class TradeResponse:
    success: bool
    code: int
    timestamp: int
    data: TradeResponseData

