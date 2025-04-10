import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from kuru_sdk.types import OrderRequest

from kuru_sdk.client_order_executor import ClientOrderExecutor

from web3 import Web3
from kuru_sdk import Orderbook, TxOptions
import os
import json
import argparse
import asyncio
from dotenv import load_dotenv
import signal

load_dotenv()

# Network and contract configuration
NETWORK_RPC = os.getenv("RPC_URL") 

print(f"NETWORK_RPC: {NETWORK_RPC}")

ADDRESSES = {
    'margin_account': '0x4B186949F31FCA0aD08497Df9169a6bEbF0e26ef',
    'orderbook': '0x05e6f736b5dedd60693fa806ce353156a1b73cf3',
    'chog': '0x7E9953A11E606187be268C3A6Ba5f36635149C81',
    'mon': '0x0000000000000000000000000000000000000000'
}

async def place_limit_buy(client: ClientOrderExecutor, price: str, size: str, post_only: bool = False, tx_options: TxOptions = TxOptions()):
    """Place a limit buy order"""

    print(f"Placing limit buy order: {size} units at {price}")

    order = OrderRequest(
        market_address=ADDRESSES['orderbook'],
        order_type='limit',
        side='buy',
        price=price,
        size=size,
        post_only=True,
        cloid="mm_1"
    )
    try:
        print(f"Placing limit buy order: {size} units at {price}")
        receipt = await client.place_order(order)
        print(f"Transaction receipt: {receipt}")
        await asyncio.sleep(10)
        return receipt
    except Exception as e:
        print(f"Error placing limit buy order: {str(e)}")
        return None
    
async def place_batch_orders(client: ClientOrderExecutor):
    orders = [
        OrderRequest(
            market_address=ADDRESSES['orderbook'],
            order_type='limit',
            side='buy',
            price=0.0000002,
            size=10000,
            cloid="mm_1"
        ),
        OrderRequest(
            market_address=ADDRESSES['orderbook'],
            order_type='limit',
            side='buy',
            price=0.0000003,
            size=10000,
            cloid="mm_2"
        ),
        OrderRequest(
            market_address=ADDRESSES['orderbook'],
            order_type='limit',
            side='sell',
            price=0.0002,
            size=10000,
            cloid="mm_3"
        )
    ]
    tx_hash = await client.batch_orders(orders)
    print(f"Batch order transaction hash: {tx_hash}")
    

async def main():
    # Define shutdown signal
    shutdown_event = asyncio.Future()

    client = ClientOrderExecutor(
        web3=Web3(Web3.HTTPProvider(NETWORK_RPC)),
        contract_address=ADDRESSES['orderbook'],
        private_key=os.getenv("PK"),
        websocket_url="wss://ws.testnet.kuru.io"
    )

    async def shutdown(sig): 
        print(f"\nReceived exit signal {sig.name}...")
        print("Disconnecting client...")
        try:
            await client.disconnect()
        except Exception as e:
            print(f"Error during disconnect: {e}")
        finally:
            print("Client disconnected.")
            shutdown_event.set_result(True)
            # Optional: Clean up signal handlers
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)

    # Add signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s)))

    try:
        print("Connecting client...")
        await client.connect()
        print("Client connected.")

        await place_limit_buy(client, 0.0000002, 10000 )
        # tx_hash = await place_batch_orders(client)
        # cancel_tx_hash = await client.cancel_orders(cloids=["mm_1"], tx_options=TxOptions())
        # print(f"Cancel transaction hash: {cancel_tx_hash}")

        print("Order placed. Running indefinitely. Press Ctrl+C to exit.")
        await shutdown_event # Wait until shutdown signal is received
    
    except asyncio.CancelledError:
        print("Main task cancelled.")
    finally:
        # Ensure disconnect is called even if there's an error before shutdown_event is awaited
        if not shutdown_event.done():
            print("Performing cleanup due to unexpected exit...")
            await client.disconnect()
            print("Client disconnected.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt caught in __main__. Exiting gracefully...")
