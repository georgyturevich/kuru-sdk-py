import asyncio
import sys
from pathlib import Path
from typing import List, Optional
import os
# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from dotenv import load_dotenv
load_dotenv()

from kuru_sdk.client import KuruClient
from kuru_sdk.types import OrderRequest, TxOptions


NETWORK_RPC = os.getenv("RPC_URL") 

ADDRESSES = {
    'margin_account': '0x4B186949F31FCA0aD08497Df9169a6bEbF0e26ef',
    'orderbook': '0x05e6f736b5dedd60693fa806ce353156a1b73cf3',
    'chog': '0x7E9953A11E606187be268C3A6Ba5f36635149C81',
    'mon': '0x0000000000000000000000000000000000000000'
}


async def place_market_buy(client: KuruClient, size: str, min_amount_out: str = "0", tx_options: TxOptions = TxOptions()):
    """Place a market buy order"""

    order = OrderRequest(
        cloid="mm_3",
        market_address=ADDRESSES['orderbook'],
        order_type='market',
        side='buy',
        size=size,
        min_amount_out=min_amount_out,
    )
    try:
        print(f"Placing market buy order: {size} units")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing market buy order: {str(e)}")
        return None
    
async def place_limit_buy(
    client: KuruClient,
    price: str = "0.000150",
    size: str = "10000",
    tx_options: TxOptions = TxOptions()
):
    order = OrderRequest(
        cloid="mm_3",
        market_address=ADDRESSES['orderbook'],
        order_type='limit',
        side='buy',
        price=price,
        size=size,
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
        private_key=os.getenv("PK"),
    )
    # await place_market_buy(client, "10")
    await place_limit_buy(client)


if __name__ == "__main__":
    asyncio.run(main())