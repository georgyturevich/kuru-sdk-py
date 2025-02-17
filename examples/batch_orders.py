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
    'orderbook': '0x05e6f736b5dedd60693fa806ce353156a1b73cf3',
    'chog': '0x7E9953A11E606187be268C3A6Ba5f36635149C81',
    'mon': '0x0000000000000000000000000000000000000000'
}

async def main():
    # Initialize the client
    client = KuruClient(
        network_rpc=NETWORK_RPC,
        margin_account_address=ADDRESSES['margin_account'],
        websocket_url=os.getenv('WS_URL'),
        private_key=os.getenv('PK')
    )

    # Create multiple order requests
    orders = [
        OrderRequest(
            market_address=ADDRESSES['orderbook'],  # Replace with your market address
            order_type="limit",
            side="buy",
            price=0.00000002,
            size=10000,
            post_only=True,
            cloid="mm-1"
        ),
        # OrderRequest(
        #     market_address=ADDRESSES['orderbook'],  # Replace with your market address
        #     order_type="limit",
        #     side="sell",
        #     price=0.00000002,
        #     size=10000,
        #     post_only=True,
        #     cloid="mm-2"
        # ),
    ]


    try:
        # Connect to WebSocket for order updates
       tx_options = TxOptions()
       await client.batch_orders(orders, tx_options)


    except Exception as e:
        print(f"Error executing batch orders: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 