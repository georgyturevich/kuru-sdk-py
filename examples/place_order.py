import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from web3 import Web3
from kuru_sdk.orderbook import Orderbook, TxOptions
import os
import json
import argparse
import asyncio
from dotenv import load_dotenv
load_dotenv()

# Network and contract configuration
NETWORK_RPC = os.getenv("RPC_URL")
print(f"NETWORK_RPC: {NETWORK_RPC}")  
ADDRESSES = {
    'orderbook': '0x336bd8b100d572cb3b4af481ace50922420e6d1b',
    'usdc': '0x34084eAEbe9Cbc209A85FFe22fa387223CDFB3e8',
    'wbtc': '0xf4f7ca3c361cA2B457Ca6AC9E393B2dad5C6b78b'
}

async def place_limit_buy(orderbook: Orderbook, price: str, size: str, post_only: bool = False, tx_options: TxOptions = TxOptions()):
    """Place a limit buy order"""
    try:
        print(f"Placing limit buy order: {size} units at {price}")
        tx_hash, order_id = await orderbook.add_buy_order(
            price=price,
            size=size,
            post_only=post_only,
            tx_options=tx_options
        )
        print(f"Transaction hash: {tx_hash}")
        print(f"Order ID: {order_id}")
        return tx_hash, order_id
    except Exception as e:
        print(f"Error placing limit buy order: {str(e)}")
        return None, None

async def place_limit_sell(orderbook: Orderbook, price: str, size: str, post_only: bool = False, tx_options: TxOptions = TxOptions()):
    """Place a limit sell order"""
    try:
        print(f"Placing limit sell order: {size} units at {price}")
        tx_hash, order_id = await orderbook.add_sell_order(
            price=price,
            size=size,
            post_only=post_only,
            tx_options=tx_options
        )
        print(f"Transaction hash: {tx_hash}")
        print(f"Order ID: {order_id}")
        return tx_hash, order_id
    except Exception as e:
        print(f"Error placing limit sell order: {str(e)}")
        return None, None

async def place_market_buy(orderbook: Orderbook, size: str, min_amount_out: str = "0", tx_options: TxOptions = TxOptions()):
    """Place a market buy order"""
    try:
        print(f"Placing market buy order: {size} units")
        tx_hash = await orderbook.market_buy(
            size=size,
            min_amount_out=min_amount_out,
            is_margin=True,
            fill_or_kill=False,
            tx_options=tx_options
        )
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing market buy order: {str(e)}")
        return None

async def place_market_sell(orderbook: Orderbook, size: str, min_amount_out: str = "0", tx_options: TxOptions = TxOptions()):
    """Place a market sell order"""
    try:
        print(f"Placing market sell order: {size} units")
        tx_hash = await orderbook.market_sell(
            size=size,
            min_amount_out=min_amount_out,
            is_margin=True,
            fill_or_kill=False,
            tx_options=tx_options
        )
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing market sell order: {str(e)}")
        return None

async def cancel_orders(orderbook: Orderbook, order_ids: list, tx_options: TxOptions = TxOptions()):
    """Cancel multiple orders"""
    try:
        print(f"Cancelling orders: {order_ids}")
        tx_hash = await orderbook.batch_cancel_orders(order_ids, tx_options)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error cancelling orders: {str(e)}")
        return None

async def batch_update(
    orderbook: Orderbook,
    buy_prices: list,
    buy_sizes: list,
    sell_prices: list,
    sell_sizes: list,
    cancel_ids: list,
    post_only: bool = False,
    tx_options: TxOptions = TxOptions()
):
    """Perform a batch update of orders"""
    try:
        print("Performing batch order update...")
        tx_hash = await orderbook.batch_orders(
            buy_prices=buy_prices,
            buy_sizes=buy_sizes,
            sell_prices=sell_prices,
            sell_sizes=sell_sizes,
            order_ids_to_cancel=cancel_ids,
            post_only=post_only,
            tx_options=tx_options
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
        'cancel', 'batch_update', 'get_l2_book'
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
        await place_limit_buy(orderbook, args.price, args.size, args.post_only)
    
    elif args.action == 'limit_sell':
        await place_limit_sell(orderbook, args.price, args.size, args.post_only)
    
    elif args.action == 'market_buy':
        await place_market_buy(orderbook, args.size, args.min_out or "0")
    
    elif args.action == 'market_sell':
        await place_market_sell(orderbook, args.size, args.min_out or "0")
    
    elif args.action == 'cancel':
        if not args.order_ids:
            print("Error: Must provide order IDs to cancel")
            return
        await cancel_orders(orderbook, args.order_ids)
    
    elif args.action == 'batch_update':
        await batch_update(
            orderbook,
            args.buy_prices or [],
            args.buy_sizes or [],
            args.sell_prices or [],
            args.sell_sizes or [],
            args.order_ids or [],
            args.post_only
        )

async def get_l2_book(orderbook: Orderbook):
    return await orderbook.fetch_orderbook()


if __name__ == "__main__":
    asyncio.run(main())
