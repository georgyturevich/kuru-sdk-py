import sys
from pathlib import Path
from typing import List, Optional


# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from kuru_sdk.client import KuruClient
from kuru_sdk.order_executor import OrderRequest

from web3 import Web3
from kuru_sdk import Orderbook, TxOptions
import os
import json
import argparse
import asyncio
from dotenv import load_dotenv
load_dotenv()

# Network and contract configuration
NETWORK_RPC = os.getenv("RPC_URL") 
ADDRESSES = {
    'margin_account': '0x4B186949F31FCA0aD08497Df9169a6bEbF0e26ef',
    'orderbook': '0x05e6f736b5dedd60693fa806ce353156a1b73cf3',
    'chog': '0x7E9953A11E606187be268C3A6Ba5f36635149C81',
    'mon': '0x0000000000000000000000000000000000000000'
}

async def place_limit_buy(client: KuruClient, price: str, size: str, post_only: bool = False, mm_id: str = "mm_1", tx_options: TxOptions = TxOptions()):
    """Place a limit buy order"""

    print(f"Placing limit buy order: {size} units at {price}")

    order = OrderRequest(
        market_address=ADDRESSES['orderbook'],
        order_type='limit',
        side='buy',
        price=price,
        size=size,
        post_only=post_only,
        cloid=mm_id
    )
    try:
        print(f"Placing limit buy order: {size} units at {price}")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing limit buy order: {str(e)}")
        return None
    
async def main():
    client = KuruClient(
        network_rpc=NETWORK_RPC,
        margin_account_address=ADDRESSES['margin_account'],
        websocket_url=os.getenv('WS_URL'),
        private_key=os.getenv('PK')
    )

    ## Create 10 limit buy orders
    all_cloids = []
    for i in range(3):
        await place_limit_buy(client, 0.00000002, 10000, True, f"mm_1_{i}")
        all_cloids.append(f"mm_1_{i}")
        print(f"Placed limit buy order {i}")

    await asyncio.sleep(10)
    ## Cancel all orders
    await client.batch_cancel_orders(ADDRESSES['orderbook'], all_cloids, TxOptions())
    print("Cancelled all orders")

if __name__ == "__main__":
    asyncio.run(main())
