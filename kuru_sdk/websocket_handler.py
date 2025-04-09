import socketio
import asyncio
import aiohttp
from typing import Optional, Callable, Dict, Any

class WebSocketHandler:
    def __init__(self,
                 websocket_url: str,
                 on_order_created: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_trade: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_order_cancelled: Optional[Callable[[Dict[str, Any]], None]] = None,
                 reconnect_interval: int = 5,
                 max_reconnect_attempts: int = 5):
        
        self.websocket_url = websocket_url
        self._session = None
        
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
            print(f"WebSocket: OrderCreated event received: {payload}")
            try:
                if self._on_order_created:
                    await self._on_order_created(payload)
            except Exception as e:
                print(f"Error in on_order_created callback: {e}")
        
        @self.sio.event
        async def Trade(payload):
            print(f"WebSocket: Trade event received: {payload}")
            try:
                if self._on_trade:
                    await self._on_trade(payload)
            except Exception as e:
                print(f"Error in on_trade callback: {e}")
        
        @self.sio.event
        async def OrdersCanceled(payload):
            print(f"WebSocket: OrderCancelled event received: {payload}")
            try:
                if self._on_order_cancelled:
                    await self._on_order_cancelled(payload)
            except Exception as e:
                print(f"Error in on_order_cancelled callback: {e}")

    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            print(self.websocket_url)
            await self.sio.connect(
                self.websocket_url,
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