import json
import os
import sys
from pathlib import Path


# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)


import asyncio
import random
from decimal import Decimal
from web3 import Web3
from kuru_sdk.order_executor import OrderExecutor, OrderRequest
from kuru_sdk.margin import MarginAccount
from kuru_sdk.orderbook import TxOptions


from dotenv import load_dotenv

load_dotenv()

# Use the same configuration as in orders.py

NETWORK_RPC = os.getenv("RPC_URL") 
ADDRESSES = {
    'margin_account': '0x4B186949F31FCA0aD08497Df9169a6bEbF0e26ef',
    'orderbook': '0xf7f70cb1a1b1128272d1c2751ab788b1226303b1',
    'icy': '0x050396c1282f28a4e32bf5ed404d578dc6f7325b',
    'mon': '0x0000000000000000000000000000000000000000'
}

async def test_order_executor():
    # Initialize Web3 and OrderExecutor
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    contract_address = ADDRESSES['orderbook']
    websocket_url = "wss://ws.testnet.kuru.io"
    private_key = os.getenv("PK")

    account = web3.eth.account.from_key(private_key)

    order_executor = OrderExecutor(
        web3=web3,
        contract_address=contract_address,
        websocket_url=websocket_url,
        private_key=private_key
    )

    # Connect to WebSocket
    await order_executor.connect()

    try:
        for i in range(2):
            print(f"Placing order {i+1}/10:")
            # Generate random order parameters
            order_type = random.choice(["limit", "market"])
            side = random.choice(["buy", "sell"])
            
            # Random price between 100 and 1000
            price = str(Decimal(random.uniform(0.00000001, 0.00000002)).quantize(Decimal('0.00000001')))
            
            # Random size between 10000 and 500000
            size = str(Decimal(random.uniform(10000, 500000)).quantize(Decimal('1')))
            
            # Random boolean flags
            post_only = random.choice([True, False])
            is_margin = random.choice([True, False])
            fill_or_kill = random.choice([True, False])
            
            # For market orders, set min_amount_out as 80% of size
            min_amount_out = str(Decimal(size) * Decimal('0.8')) if order_type == "market" else None

            # Create order request
            order = OrderRequest(
                market_address=ADDRESSES['orderbook'],
                order_type=order_type,
                side=side,
                price=price if order_type == "limit" else None,
                size=size,
                post_only=post_only,
                is_margin=is_margin,
                fill_or_kill=fill_or_kill,
                min_amount_out=min_amount_out
            )

            # Generate a unique client order ID (CLOID)
            cloid = f"order_{i}"

            try:
                print(f"\nPlacing order {i+1}/2:")
                print(f"CLOID: {cloid}")
                print(f"Type: {order_type}")
                print(f"Side: {side}")
                print(f"Price: {price if order_type == 'limit' else 'N/A'}")
                print(f"Size: {size}")
                print(f"Min Amount Out: {min_amount_out if order_type == 'market' else 'N/A'}")

                # Place the order
                tx_options = TxOptions()
                tx_hash = await order_executor.place_order(order, tx_options)
                print(f"Transaction hash: {tx_hash}")

                # Wait for order confirmation
                # You might want to adjust the sleep time based on your network
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Error placing order {i+1}: {str(e)}")

            await asyncio.sleep(1)


    finally:
        print("order_executor.cloid_to_order: ", order_executor.cloid_to_order)
        print("order_executor.executed_trades: ", order_executor.executed_trades)
        print("order_executor.cancelled_orders: ", order_executor.cancelled_orders)
        await order_executor.disconnect()

# Run the script
if __name__ == "__main__":
    asyncio.run(test_order_executor())
