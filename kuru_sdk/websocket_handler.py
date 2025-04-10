import socketio
import asyncio
import aiohttp
from typing import Optional, Callable
from kuru_sdk.types import OrderCreatedPayload, TradePayload, OrderCancelledPayload, MarketParams

class WebSocketHandler:
    def __init__(self,
                 websocket_url: str,
                 market_address: str,
                 market_params: MarketParams,
                 on_order_created: Optional[Callable[[OrderCreatedPayload], None]] = None,
                 on_trade: Optional[Callable[[TradePayload], None]] = None,
                 on_order_cancelled: Optional[Callable[[OrderCancelledPayload], None]] = None,
                 reconnect_interval: int = 5,
                 max_reconnect_attempts: int = 5):
        
        self.websocket_url = websocket_url
        self.market_address = market_address
        self._session = None

        self.market_params = market_params
        
        # Store callback functions
        self._on_order_created = on_order_created
        self._on_trade = on_trade
        self._on_order_cancelled = on_order_cancelled
        
        # Create Socket.IO client with specific configuration
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=max_reconnect_attempts,
            reconnection_delay=reconnect_interval,
            reconnection_delay_max=reconnect_interval * 2,
            logger=True,
            engineio_logger=True
        )
        
        # Register event handlers
        @self.sio.event
        async def connect():
            print(f"Connected to WebSocket server at {websocket_url}")
        
        @self.sio.event
        async def disconnect():
            print("Disconnected from WebSocket server")
        
        @self.sio.event
        async def OrderCreated(payload):
            formatted_payload = self._format_order_created_payload(payload)
            print(f"OrderCreated Event Received: {formatted_payload}")
            try:
                if self._on_order_created:
                    await self._on_order_created(formatted_payload)
            except Exception as e:
                print(f"Error in on_order_created callback: {e}")
        
        @self.sio.event
        async def Trade(payload):
            formatted_payload = self._format_trade_payload(payload)
            print(f"Trade Event Received: {formatted_payload}")
            try:
                if self._on_trade:
                    await self._on_trade(formatted_payload)
            except Exception as e:
                print(f"Error in on_trade callback: {e}")
        
        @self.sio.event
        async def OrdersCanceled(payload):
            formatted_payload = self._format_order_cancelled_payload(payload)
            print(f"OrdersCanceled Event Received: {formatted_payload}")
            try:
                if self._on_order_cancelled:
                    await self._on_order_cancelled(formatted_payload)
            except Exception as e:
                print(f"Error in on_order_cancelled callback: {e}")

    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            print(self.websocket_url)
            await self.sio.connect(
                f"{self.websocket_url}?marketAddress={self.market_address}",
                transports=['websocket']
            )
            print(f"Successfully connected to {self.websocket_url}")
            
            # Keep the connection alive in the background
            asyncio.create_task(self.sio.wait())
        except Exception as e:
            print(f"Failed to connect to WebSocket server: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        try:
            await self.sio.disconnect()
            if self._session:
                await self._session.close()
                self._session = None
            print("Disconnected from WebSocket server")
        except Exception as e:
            print(f"Error during disconnect: {e}")
            raise

    def is_connected(self) -> bool:
        """Check if the WebSocket is currently connected"""
        return self.sio.connected
    
    def _format_order_created_payload(self, payload) -> OrderCreatedPayload:
        return OrderCreatedPayload(
            order_id=payload['orderId'],
            market_address=payload['marketAddress'],
            owner=payload['owner'],
            price=float(payload['price']) / float(str(self.market_params.price_precision)),
            size=float(payload['size']) / float(str(self.market_params.size_precision)),
            is_buy=payload['isBuy'],
            block_number=payload['blockNumber'],
            tx_index=payload['txIndex'],
            log_index=payload['logIndex'],
            transaction_hash=payload['transactionHash'],
            trigger_time=payload['triggerTime'],
            remaining_size=float(payload['remainingSize']) / float(str(self.market_params.size_precision)),
            is_canceled=payload['isCanceled'],
        )
    
    def _format_trade_payload(self, payload) -> TradePayload:
        return TradePayload(
            order_id=payload['orderId'],
            market_address=payload['marketAddress'],
            maker_address=payload['makerAddress'],
            is_buy=payload['isBuy'],
            price=float(payload['price']) / float(str(self.market_params.price_precision)),
            updated_size=float(payload['updatedSize']) / float(str(self.market_params.size_precision)),
            taker_address=payload['takerAddress'],
            filled_size=float(payload['filledSize']) / float(str(self.market_params.size_precision)),
            block_number=payload['blockNumber'],
            tx_index=payload['txIndex'],
            log_index=payload['logIndex'],
            transaction_hash=payload['transactionHash'],
            trigger_time=payload['triggerTime'],
        )
    
    def _format_order_cancelled_payload(self, payload) -> OrderCancelledPayload:
        return OrderCancelledPayload(
            order_ids=payload['orderIds'],
            maker_address=payload['makerAddress'],
            canceled_orders_data=[self._format_order_created_payload(order) for order in payload['canceledOrdersData']],
        )
