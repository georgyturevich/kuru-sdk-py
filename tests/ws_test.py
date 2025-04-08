import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from kuru_sdk.websocket_handler import WebSocketHandler
import asyncio
ws = WebSocketHandler(
    websocket_url="wss://ws.testnet.kuru.io?marketAddress=0xf7f70cb1a1b1128272d1c2751ab788b1226303b1",
)

asyncio.run(ws.connect())