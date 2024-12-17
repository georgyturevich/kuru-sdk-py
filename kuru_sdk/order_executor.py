from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
import asyncio
import socketio

from web3 import Web3
from .orderbook import Orderbook, TxOptions

@dataclass
class OrderRequest:
    cloid: Optional[str] = None
    market_address: str
    order_type: Literal["limit", "market"]
    side: Literal["buy", "sell"]
    price: Optional[str] = None  # Optional for market orders
    size: str = ""
    post_only: bool = False
    is_margin: bool = False
    fill_or_kill: bool = False
    min_amount_out: Optional[str] = None  # For market orders

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
        print(f"websocket_url: {self.websocket_url}")
        
        # Initialize socket.io client
        self.sio = socketio.AsyncClient()
        
        # Initialize storage dictionaries
        self.cloid_to_tx: Dict[str, str] = {}
        self.tx_to_cloid: Dict[str, str] = {}
        self.cloid_to_order: Dict[str, OrderCreatedEvent] = {}
        self.cloid_to_order_id: Dict[str, int] = {}
        self.executed_trades: Dict[int, List[TradeEvent]] = {}
        self.cancelled_orders: Dict[int, str] = {}

        self.on_order_created = on_order_created
        self.on_trade = on_trade
        self.on_order_cancelled = on_order_cancelled

        
        # Create event queues/channels
        self.order_created_channel = asyncio.Queue()
        self.trade_channel = asyncio.Queue()
        self.order_cancelled_channel = asyncio.Queue()

        # Register socket.io event handlers
        @self.sio.on('connect')
        async def on_connect():
            print(f"Connected to WebSocket server at {websocket_url}")

        @self.sio.on('disconnect')
        async def on_disconnect():
            print("Disconnected from WebSocket server")

        @self.sio.on('OrderCreated')
        async def on_order_created(payload):
            print(f"on_order_created: {payload}")
            tx_hash = payload.get('transactionHash')
            print(f"tx_hash in self.tx_to_cloid: {tx_hash in self.tx_to_cloid}")
            if tx_hash in self.tx_to_cloid:
                cloid = self.tx_to_cloid[tx_hash]
                print(f"Order created for CLOID: {cloid}, TX: {tx_hash}")
                order_event = OrderCreatedEvent.from_dict(payload)
                self.cloid_to_order[cloid] = order_event
                self.cloid_to_order_id[cloid] = order_event.orderId
                
                await self.order_created_channel.put((cloid, order_event))
                if self.on_order_created:
                    await self.on_order_created(order_event)

        @self.sio.on('Trade')
        async def on_trade(payload):
            print(f"on_trade: {payload}")
            order_id = payload.get('orderId')
            tx_hash = payload.get('transactionHash')
            if order_id in self.cloid_to_order_id:
                cloid = self.cloid_to_order_id[order_id]
                print(f"Trade executed for CLOID: {cloid}, Order ID: {order_id}")
                trade_event = TradeEvent.from_dict(payload)
                if self.executed_trades.get(cloid):
                    self.executed_trades[cloid].append(trade_event)
                else:
                    self.executed_trades[cloid] = [trade_event]
                await self.trade_channel.put((cloid, trade_event))
                await self.on_trade(trade_event)
            if tx_hash in self.tx_to_cloid:
                cloid = self.tx_to_cloid[tx_hash]
                print(f"Trade executed for CLOID: {cloid}, TX: {tx_hash}")
                trade_event = TradeEvent.from_dict(payload)
                if self.executed_trades.get(cloid):
                    self.executed_trades[cloid].append(trade_event)
                else:
                    self.executed_trades[cloid] = [trade_event]
                await self.trade_channel.put((cloid, trade_event))
                if self.on_trade:
                    await self.on_trade(trade_event)

        @self.sio.on('OrderCancelled')
        async def on_order_cancelled(payload):
            print(f"on_order_cancelled: {payload}")
            order_id = payload.get('orderId')
            if order_id in self.cloid_to_order_id:
                cloid = self.cloid_to_order_id[order_id]
                print(f"Order cancelled for CLOID: {cloid}, Order ID: {order_id}")
                self.cancelled_orders[order_id] = cloid
                await self.order_cancelled_channel.put((cloid, payload))
                if self.on_order_cancelled:
                    await self.on_order_cancelled(payload)
                del self.cloid_to_order_id[order_id]
                del self.cloid_to_order[cloid]

    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            await self.sio.connect(self.websocket_url)
            print(f"Successfully connected to {self.websocket_url}")
        except Exception as e:
            print(f"Failed to connect to WebSocket server: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        await self.sio.disconnect()
        print("Disconnected from WebSocket server")

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

        print(f"Orderbook address: {self.orderbook.contract_address}")

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
                        tx_options=tx_options
                    )
                    print(f"tx_hash: {tx_hash}")
                else:  # sell
                    tx_hash = await self.orderbook.add_sell_order(
                        price=order.price,
                        size=order.size,
                        post_only=order.post_only,
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
            tx_hash = f"0x{tx_hash}".lower()
            print(f"tx_hash: {tx_hash}")
            if tx_hash and cloid:
                self._store_order_mapping(cloid, tx_hash)
            
            return tx_hash

        except Exception as e:
            print(f"Error placing order: {e}")
            raise

    async def batch_cancel_orders(self, cloids: List[str], tx_options: Optional[TxOptions] = TxOptions()):
        order_ids = [self.cloid_to_order_id[cloid] for cloid in cloids]
        await self.orderbook.batch_cancel_orders(order_ids, tx_options)

    def get_tx_hash_by_cloid(self, cloid: str) -> Optional[str]:
        """Get transaction hash for a given CLOID"""
        return self.cloid_to_tx.get(cloid)

    def get_cloid_by_tx_hash(self, tx_hash: str) -> Optional[str]:
        """Get CLOID for a given transaction hash"""
        return self.tx_to_cloid.get(tx_hash)


async def listen_for_events(order_executor):
    while True:
        # Listen for order created events
        cloid, order_event = await order_executor.order_created_channel.get()
        print(f"Received order created event for {cloid}: {order_event}")

        # Listen for trade events
        cloid, trade = await order_executor.trade_channel.get()
        print(f"Received trade event for {cloid}: {trade}")

        # Listen for cancellation events
        cloid, cancellation = await order_executor.order_cancelled_channel.get()
        print(f"Received cancellation event for {cloid}: {cancellation}")

    