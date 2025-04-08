import socketio
import asyncio
import aiohttp
import logging
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
        self.logger = logging.getLogger(__name__)
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
            self.logger.info(f"Connected to WebSocket server at {websocket_url}")
        
        @self.sio.event
        async def disconnect():
            self.logger.warning("Disconnected from WebSocket server")
        
        @self.sio.event
        async def OrderCreated(payload):
            self.logger.debug(f"WebSocket: OrderCreated event received: {payload}")
            try:
                if self._on_order_created:
                    await self._on_order_created(payload)
            except Exception as e:
                self.logger.error(f"Error in on_order_created callback: {e}")
        
        @self.sio.event
        async def Trade(payload):
            self.logger.debug(f"WebSocket: Trade event received: {payload}")
            try:
                if self._on_trade:
                    await self._on_trade(payload)
            except Exception as e:
                self.logger.error(f"Error in on_trade callback: {e}")
        
        @self.sio.event
        async def OrdersCanceled(payload):
            self.logger.debug(f"WebSocket: OrderCancelled event received: {payload}")
            try:
                if self._on_order_cancelled:
                    await self._on_order_cancelled(payload)
            except Exception as e:
                self.logger.error(f"Error in on_order_cancelled callback: {e}")

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
            self.logger.info(f"Successfully connected to {self.websocket_url}")
            
            # Keep the connection alive
            await self.sio.wait()
        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket server: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        try:
            await self.sio.disconnect()
            if self._session:
                await self._session.close()
                self._session = None
            self.logger.info("Disconnected from WebSocket server")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
            raise

    def is_connected(self) -> bool:
        """Check if the WebSocket is currently connected"""
        return self.sio.connected