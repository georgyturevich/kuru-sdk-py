import sys
from pathlib import Path
from typing import List, Optional


# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from kuru_sdk.client import KuruClient
from kuru_sdk.order_executor import OrderRequest, TxOptions
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Network and contract configuration
NETWORK_RPC = os.getenv("RPC_URL") 
ADDRESSES = {
    'margin_account': '0x4B186949F31FCA0aD08497Df9169a6bEbF0e26ef',
    'orderbook': '0xf7f70cb1a1b1128272d1c2751ab788b1226303b1',
    'chog': '0x050396c1282f28a4e32bf5ed404d578dc6f7325b',
    'mon': '0x0000000000000000000000000000000000000000'
}

async def main():
    # Initialize the client
    client = KuruClient(
        network_rpc=NETWORK_RPC,
        margin_account_address=ADDRESSES['margin_account'],
        websocket_url=None,
        private_key=os.getenv('PK')
    )
    # Create multiple order requests
    orders = [
        OrderRequest(
            market_address=ADDRESSES['orderbook'],  # Replace with your market address
            order_type="limit",
            side="buy",
            price=0.00000002,
            size=100,
            post_only=True,
            cloid="mm-1"
        ),
        OrderRequest(
            market_address=ADDRESSES['orderbook'],  # Replace with your market address
            order_type="limit",
            side="buy",
            price=0.00000002,
            size=100,
            post_only=True,
            cloid="mm-2"
        ),
    ]


    try:
        # Connect to WebSocket for order updates
       tx_options = TxOptions()
       await client.batch_orders(orders, tx_options)


    except Exception as e:
        print(f"Error executing batch orders: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 