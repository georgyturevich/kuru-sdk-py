import asyncio
import socketio
from typing import Optional

import asyncio
import socketio
from typing import Optional

class WebSocketHandler:
    def __init__(self,
                 websocket_url: str,
                 on_order_created: Optional[callable] = None,
                 on_trade: Optional[callable] = None,
                 on_order_cancelled: Optional[callable] = None):
        
        self.websocket_url = websocket_url
        self.sio = socketio.AsyncClient()
      
        
        # Store callback functions
        self._on_order_created = on_order_created
        self._on_trade = on_trade
        self._on_order_cancelled = on_order_cancelled
        
        # Register socket.io event handlers
        @self.sio.on('connect')
        async def on_connect():
            print(f"Connected to WebSocket server at {websocket_url}")

        @self.sio.on('disconnect')
        async def on_disconnect():
            print("Disconnected from WebSocket server")

        @self.sio.on('OrderCreated')
        async def on_order_created(payload):
            print(f"WebSocket: OrderCreated event received: {payload}")
            if self._on_order_created:
                await self._on_order_created(payload)

        @self.sio.on('Trade')
        async def on_trade(payload):
            print(f"WebSocket: Trade event received: {payload}")
            if self._on_trade:
                await self._on_trade(payload)

        @self.sio.on('OrderCancelled')
        async def on_order_cancelled(payload):
            print(f"WebSocket: OrderCancelled event received: {payload}")
            if self._on_order_cancelled:
                await self._on_order_cancelled(payload)

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