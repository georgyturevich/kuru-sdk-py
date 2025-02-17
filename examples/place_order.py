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

async def place_limit_buy(client: KuruClient, price: str, size: str, post_only: bool = False, tx_options: TxOptions = TxOptions()):
    """Place a limit buy order"""

    print(f"Placing limit buy order: {size} units at {price}")

    order = OrderRequest(
        market_address=ADDRESSES['orderbook'],
        order_type='limit',
        side='buy',
        price=price,
        size=size,
        post_only=post_only,
        cloid="mm_1"
    )
    try:
        print(f"Placing limit buy order: {size} units at {price}")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        await asyncio.sleep(10)
        return tx_hash
    except Exception as e:
        print(f"Error placing limit buy order: {str(e)}")
        return None

async def place_limit_sell(client: KuruClient, price: str, size: str, post_only: bool = False, tx_options: TxOptions = TxOptions()):
    """Place a limit sell order"""

    order = OrderRequest(
        market_address=ADDRESSES['orderbook'],
        order_type='limit',
        side='sell',
        price=price,
        size=size,
        post_only=post_only,
        cloid="mm_2"
    )
    try:
        print(f"Placing limit sell order: {size} units at {price}")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing limit sell order: {str(e)}")
        return None, None

async def place_market_buy(client: KuruClient, size: str, min_amount_out: str = "0", tx_options: TxOptions = TxOptions()):
    """Place a market buy order"""

    order = OrderRequest(
        market_address=ADDRESSES['orderbook'],
        order_type='market',
        side='buy',
        size=size,
        min_amount_out=min_amount_out,
        cloid="mm_3"
    )
    try:
        print(f"Placing market buy order: {size} units")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing market buy order: {str(e)}")
        return None

async def place_market_sell(client: KuruClient, size: str, min_amount_out: str = "0", tx_options: TxOptions = TxOptions()):
    """Place a market sell order"""

    order = OrderRequest(
        market_address=ADDRESSES['orderbook'],
        order_type='market',
        side='sell',
        size=size,
        min_amount_out=min_amount_out,
        cloid="mm_4"
    )
    try:
        print(f"Placing market sell order: {size} units")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing market sell order: {str(e)}")
        return None

async def cancel_orders(client: KuruClient, order_ids: list, tx_options: TxOptions = TxOptions()):
    """Cancel multiple orders"""
    try:
        print(f"Cancelling orders: {order_ids}")
        tx_hash = await client.batch_cancel_orders(order_ids, tx_options)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error cancelling orders: {str(e)}")
        return None

async def batch_update(
    client: KuruClient,
    order_requests: List[OrderRequest],
    tx_options: Optional[TxOptions] = None
):
    """Perform a batch update of orders"""
    try:
        print("Performing batch order update...")
        tx_hash = await client.batch_orders(
            order_requests,
            tx_options
        )
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error performing batch update: {str(e)}")
        return None

async def main():

    parser = argparse.ArgumentParser(description='Place and manage orders on the orderbook')
    parser.add_argument('action', choices=[
        'limit_buy', 'limit_sell', 'market_buy', 'market_sell',
        'cancel', 'get_l2_book', 'batch_update'
    ], help='Action to perform')
    
    # Add action-specific arguments
    parser.add_argument('--price', type=str, help='Price for limit orders')
    parser.add_argument('--size', type=str, help='Size of the order')
    parser.add_argument('--min-out', type=str, help='Minimum amount out for market orders')
    parser.add_argument('--post-only', action='store_true', help='Make order post-only')
    parser.add_argument('--order-ids', type=int, nargs='+', help='Order IDs for cancellation')
    
    # Batch update specific arguments
    parser.add_argument('--buy-prices', type=str, nargs='+', help='Prices for batch buy orders')
    parser.add_argument('--buy-sizes', type=str, nargs='+', help='Sizes for batch buy orders')
    parser.add_argument('--sell-prices', type=str, nargs='+', help='Prices for batch sell orders')
    parser.add_argument('--sell-sizes', type=str, nargs='+', help='Sizes for batch sell orders')
    
    args = parser.parse_args()

    # Initialize Web3 and Orderbook
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    private_key = os.getenv('PK', "")

    print("WS_URL: ", os.getenv('WS_URL'))

    client = KuruClient(
        network_rpc=NETWORK_RPC,
        margin_account_address=ADDRESSES['margin_account'],
        websocket_url=os.getenv('WS_URL'),
        private_key=os.getenv('PK')
    )
    
    orderbook = Orderbook(
        web3=web3,
        contract_address=ADDRESSES['orderbook'],
        private_key=private_key
    )

    if args.action == 'get_l2_book':
        l2_book = await get_l2_book(orderbook)
        print(l2_book)
        return

    if args.action == 'limit_buy':
        await place_limit_buy(client, args.price, args.size, args.post_only)
    
    elif args.action == 'limit_sell':
        await place_limit_sell(client, args.price, args.size, args.post_only)
    
    elif args.action == 'market_buy':
        await place_market_buy(client, args.size, args.min_out or "0")
    
    elif args.action == 'market_sell':
        await place_market_sell(client, args.size, args.min_out or "0")
    
    elif args.action == 'cancel':
        if not args.order_ids:
            print("Error: Must provide order IDs to cancel")
            return
        await cancel_orders(orderbook, args.order_ids)

    elif args.action == 'batch_update':
        order_requests = [
            OrderRequest(
                market_address=ADDRESSES['orderbook'],
                order_type='market',
                side='buy',
                size=1,
                min_amount_out=args.min_out or "0",
                cloid="mm_1"
            ),
            OrderRequest(
                market_address=ADDRESSES['orderbook'],
                order_type='limit',
                side='sell',
                price=0.00000002,
                size=1,
                cloid="mm_2"
            ),
            OrderRequest(
                market_address=ADDRESSES['orderbook'],
                order_type='market',
                side='sell',
                size=1,
                min_amount_out=args.min_out or "0",
                cloid="mm_3"
            )
        ]
        await batch_update(client, order_requests)

async def get_l2_book(orderbook: Orderbook):
    return await orderbook.fetch_orderbook()


if __name__ == "__main__":
    asyncio.run(main())
