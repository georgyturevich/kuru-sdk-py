from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
import asyncio
import socketio
import json

from web3 import Web3

from kuru_sdk.websocket_handler import WebSocketHandler
from .orderbook import Orderbook, TxOptions

@dataclass
class OrderRequest:
    market_address: str
    order_type: Literal["limit", "market", "cancel"]
    side: Literal["buy", "sell"]
    price: Optional[str] = None  # Optional for market orders
    size: Optional[str] = None
    post_only: Optional[bool] = None
    is_margin: Optional[bool] = False
    fill_or_kill: Optional[bool] = False
    min_amount_out: Optional[str] = None  # For market orders
    cancel_order_ids: Optional[List[int | str]] = None # For batch cancel
    cancel_cloids: Optional[List[str]] = None
    cloid: Optional[str] = None
    tick_normalization: Optional[str] = None

@dataclass
class OrderCreatedEvent:
    orderId: int
    marketAddress: str
    owner: str
    size: str
    price: str
    isBuy: bool
    blockNumber: str
    txIndex: int
    logIndex: int
    transactionHash: str
    triggerTime: str  # ISO format datetime string
    remainingSize: str
    isCanceled: bool

    @classmethod
    def from_dict(cls, data: Dict) -> 'OrderCreatedEvent':
        return cls(
            orderId=int(data['orderId']),
            marketAddress=data['marketAddress'],
            owner=data['owner'],
            size=data['size'],
            price=data['price'],
            isBuy=data['isBuy'],
            blockNumber=data['blockNumber'],
            txIndex=data['txIndex'],
            logIndex=data['logIndex'],
            transactionHash=data['transactionHash'],
            triggerTime=data['triggerTime'],
            remainingSize=data['remainingSize'],
            isCanceled=data['isCanceled']
        )

@dataclass
class TradeEvent:
    orderId: int
    marketAddress: str
    makerAddress: str
    takerAddress: str
    isBuy: bool
    price: str
    updatedSize: str
    filledSize: str
    blockNumber: str
    txIndex: int
    logIndex: int
    transactionHash: str
    triggerTime: str  # ISO format datetime string

    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeEvent':
        return cls(
            orderId=int(data['orderId']),
            marketAddress=data['marketAddress'],
            makerAddress=data['makerAddress'],
            takerAddress=data['takerAddress'],
            isBuy=data['isBuy'],
            price=data['price'],
            updatedSize=data['updatedSize'],
            filledSize=data['filledSize'],
            blockNumber=data['blockNumber'],
            txIndex=data['txIndex'],
            logIndex=data['logIndex'],
            transactionHash=data['transactionHash'],
            triggerTime=data['triggerTime']
        )

class OrderExecutor:
    def __init__(self, 
                 web3: Web3,
                 contract_address: str,
                 websocket_url: str,
                 private_key: str,
                 on_order_created: Optional[callable] = None,
                 on_trade: Optional[callable] = None,
                 on_order_cancelled: Optional[callable] = None):
        """
        Initialize OrderExecutor with WebSocket connection
        
        Args:
            web3: Web3 instance
            contract_address: Address of the deployed contract
            websocket_url: URL for the WebSocket connection
            private_key: Private key for signing transactions (optional)
        """
        self.orderbook = Orderbook(web3, contract_address, private_key)
        self.websocket_url = f"{websocket_url}?marketAddress={contract_address.lower()}"
        
        # Initialize socket.io client
        self.sio = socketio.AsyncClient()
        
        # Initialize storage dictionaries
        self.cloid_to_tx: Dict[str, str] = {}
        self.tx_to_cloid: Dict[str, str] = {}
        self.cloid_to_order: Dict[str, OrderCreatedEvent] = {}
        self.cloid_to_order_id: Dict[str, int] = {}
        self.order_id_to_cloid: Dict[int, str] = {}
        self.executed_trades: Dict[int, List[TradeEvent]] = {}
        self.cancelled_orders: Dict[int, str] = {}

        self.on_order_created = on_order_created
        self.on_trade = on_trade
        self.on_order_cancelled = on_order_cancelled

        self.ws_handler = WebSocketHandler(
            websocket_url=self.websocket_url,
            on_order_created=self._handle_order_created,
            on_trade=self._handle_trade,
            on_order_cancelled=self._handle_order_cancelled
        )


    async def _handle_order_created(self, payload):
        print(f"Received order created event: {payload}")
        try:
            # Parse the payload into an OrderCreatedEvent
            if isinstance(payload, dict):
                tx_hash = payload.get('transactionHash')
                order_event = OrderCreatedEvent.from_dict(payload)
            elif isinstance(payload, str):
                data = json.loads(payload)
                tx_hash = data.get('transactionHash')
                order_event = OrderCreatedEvent.from_dict(data)
            else:
                tx_hash = payload.transactionHash
                order_event = payload

            # Look up the CLOID using the transaction hash
            if tx_hash in self.tx_to_cloid:
                cloid = self.tx_to_cloid[tx_hash]
                print(f"Order created for CLOID: {cloid}, TX: {tx_hash}")
                
                # Store the order event and order ID
                self.cloid_to_order[cloid] = order_event
                self.cloid_to_order_id[cloid] = order_event.orderId
                self.order_id_to_cloid[order_event.orderId] = cloid
            if self.on_order_created:
                self.on_order_created(payload)

        except Exception as e:
            print(f"Error handling order created event: {e}")

    async def _handle_trade(self, payload):
        # Initialize trade_event before any conditional blocks
        trade_event = None
        
        try:
            # Your existing trade event parsing logic
            if isinstance(payload, dict):
                trade_event = payload
            elif isinstance(payload, str):
                trade_event = json.loads(payload)

            order_id = trade_event.get('orderId')
            tx_hash = trade_event.get('transactionHash')
            if order_id in self.cloid_to_order_id:
                cloid = self.cloid_to_order_id[order_id]
                print(f"Trade executed for CLOID: {cloid}, Order ID: {order_id}")
                if self.executed_trades.get(cloid):
                    self.executed_trades[cloid].append(trade_event)
                else:
                    self.executed_trades[cloid] = [trade_event]

            if tx_hash in self.tx_to_cloid:
                cloid = self.tx_to_cloid[tx_hash]
                print(f"Trade executed for CLOID: {cloid}, TX: {tx_hash}")
                if self.executed_trades.get(cloid):
                    self.executed_trades[cloid].append(trade_event)
                else:
                    self.executed_trades[cloid] = [trade_event]
            
            # Only call on_trade if we have a valid trade_event
            if trade_event and self.on_trade:
                self.on_trade(trade_event)
                
        except Exception as e:
            print(f"Error handling trade event: {e}")

    async def _handle_order_cancelled(self, payload):
        order_event = None
        try:
            if isinstance(payload, dict):
                order_event = payload
            elif isinstance(payload, str):
                order_event = json.loads(payload)

            order_id = order_event.get('orderId')
            if order_id in self.cloid_to_order_id:
                    cloid = self.cloid_to_order_id[order_id]
                    print(f"Order cancelled for CLOID: {cloid}, Order ID: {order_id}")
                    self.cancelled_orders[order_id] = cloid
                    del self.cloid_to_order_id[order_id]
                    del self.cloid_to_order[cloid]
                    del self.order_id_to_cloid[order_id]
            if self.on_order_cancelled:
                self.on_order_cancelled(payload)

        except Exception as e:
            print(f"Error handling order cancelled event: {e}")

    async def connect(self):
        """Connect to the WebSocket server"""
        print(f"Connecting to WebSocket server: {self.websocket_url}")
        await self.ws_handler.connect()

    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        await self.ws_handler.disconnect()

    def _store_order_mapping(self, cloid: str, tx_hash: str):
        self.cloid_to_tx[cloid] = tx_hash
        self.tx_to_cloid[tx_hash] = cloid
        print(f"Stored mapping - CLOID: {cloid}, TX: {tx_hash}")

    async def place_order(self, order: OrderRequest, tx_options: Optional[TxOptions] = TxOptions()) -> str:
        """
        Place an order with the given parameters
        Returns the transaction hash
        """

        cloid = order.cloid

        try:
            tx_hash = None
            if order.order_type == "limit":
                if not order.price:
                    raise ValueError("Price is required for limit orders")
                
                if order.side == "buy":
                    print(f"Adding buy order with price: {order.price}, size: {order.size}, post_only: {order.post_only}, tx_options: {tx_options}")
                    tx_hash = await self.orderbook.add_buy_order(
                        price=order.price,
                        size=order.size,
                        post_only=order.post_only,
                        tick_normalization=order.tick_normalization,
                        tx_options=tx_options
                    )
                else:  # sell
                    tx_hash = await self.orderbook.add_sell_order(
                        price=order.price,
                        size=order.size,
                        post_only=order.post_only,
                        tick_normalization=order.tick_normalization,
                        tx_options=tx_options
                    )
            else:  # market
                if not order.min_amount_out:
                    raise ValueError("min_amount_out is required for market orders")
                
                if order.side == "buy":
                    tx_hash = await self.orderbook.market_buy(
                        size=order.size,
                        min_amount_out=order.min_amount_out,
                        is_margin=order.is_margin,
                        fill_or_kill=order.fill_or_kill,
                        tx_options=tx_options
                    )
                else:  # sell
                    tx_hash = await self.orderbook.market_sell(
                        size=order.size,
                        min_amount_out=order.min_amount_out,
                        is_margin=order.is_margin,
                        fill_or_kill=order.fill_or_kill,
                        tx_options=tx_options
                    )

            if order.order_type == "cancel":
                tx_hash = await self.orderbook.batch_orders(order_ids_to_cancel=order.order_ids, tx_options=tx_options)

            tx_hash = f"0x{tx_hash}".lower()
            if tx_hash and cloid:
                self._store_order_mapping(cloid, tx_hash)
            
            return tx_hash

        except Exception as e:
            print(f"Error placing order: {e}")
            raise
    

    async def batch_orders(self, order_requests: List[OrderRequest], tx_options: Optional[TxOptions] = TxOptions()):
        buy_prices = []
        buy_sizes = []
        sell_prices = []
        sell_sizes = []
        order_ids_to_cancel = []
        post_only = False  # Will be set to True if any order is post_only

        # Sort orders into buy and sell lists
        for order in order_requests:

            if order.order_type == 'cancel':
                for order_id in order.order_ids:
                    order_ids_to_cancel.append(order_id)
                continue

            if order.side == "buy":
                buy_prices.append(order.price)
                buy_sizes.append(order.size)
            elif order.side == "sell":  # sell
                sell_prices.append(order.price)
                sell_sizes.append(order.size)
            
            post_only = post_only or order.post_only

        # Execute batch order
        tx_hash = await self.orderbook.batch_orders(
            buy_prices=buy_prices,
            buy_sizes=buy_sizes,
            sell_prices=sell_prices,
            sell_sizes=sell_sizes,
            order_ids_to_cancel=order_ids_to_cancel,
            post_only=post_only,
            tx_options=tx_options
        )

        # Store order mappings if cloid is provided
        tx_hash = f"0x{tx_hash}".lower()
        if tx_hash and order_requests[0].cloid:
            self._store_order_mapping(order_requests[0].cloid, tx_hash)
        
        return tx_hash
    
    async def batch_cancel_orders(self, cloids: List[str], tx_options: Optional[TxOptions] = TxOptions()):
        order_ids = [self.cloid_to_order_id[cloid] for cloid in cloids]
        print(f"Cancelling orders with order IDs: {order_ids}")
        tx_hash = await self.orderbook.batch_cancel_orders(order_ids, tx_options)
        return tx_hash

    def get_tx_hash_by_cloid(self, cloid: str) -> Optional[str]:
        """Get transaction hash for a given CLOID"""
        return self.cloid_to_tx.get(cloid)

    def get_cloid_by_tx_hash(self, tx_hash: str) -> Optional[str]:
        """Get CLOID for a given transaction hash"""
        return self.tx_to_cloid.get(tx_hash)

    def get_all_executed_trades(self) -> List[TradeEvent]:
        """Get all executed trades"""
        return [trade for trades in self.executed_trades.values() for trade in trades]
    
    def get_all_cancelled_orders(self) -> List[str]:
        """Get all cancelled orders"""
        return list(self.cancelled_orders.keys())
    
    def get_order_id_by_cloid(self, cloid: str) -> int:
        """Get order ID for a given CLOID"""
        return self.cloid_to_order_id.get(cloid)
