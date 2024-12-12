import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

import asyncio
import time
from decimal import Decimal
from web3 import Web3

from src.order_executor import OrderExecutor, OrderRequest
from src.orderbook import TxOptions

import os
from dotenv import load_dotenv

load_dotenv()

async def place_single_order():
    # Configuration
    NETWORK_RPC = os.getenv("RPC_URL")
    CONTRACT_ADDRESS = '0x336bd8b100d572cb3b4af481ace50922420e6d1b'  # orderbook address
    WEBSOCKET_URL = 'https://ws.staging.kuru.io'
    PRIVATE_KEY = os.getenv("PK")
    USER_ADDRESS = '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'

    # Initialize Web3 and OrderExecutor
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    order_executor = OrderExecutor(
        web3=web3,
        contract_address=CONTRACT_ADDRESS,
        websocket_url=WEBSOCKET_URL,
        private_key=PRIVATE_KEY
    )

    try:
        await order_executor.connect()

        # Base order template
        order = OrderRequest(
            order_type="limit",
            side="buy",
            price="179.1",
            size="0.1",
            post_only=False
        )

        # First order - no TX options
        start = time.time()
        tx_hash1 = await order_executor.place_order(order, "order_1")
        event1 = await order_executor.order_created_channel.get()
        print(f"Order 1 (No TX options) total time: {(time.time() - start):.3f} seconds")

        # Second order - with basic TX options
        start = time.time()
        tx_options = TxOptions(
            gas_limit=140000,
            gas_price=1000000000,
            max_priority_fee_per_gas=0
        )
        tx_hash2 = await order_executor.place_order(order, "order_2", tx_options)
        event2 = await order_executor.order_created_channel.get()
        print(f"Order 2 (Basic TX options) total time: {(time.time() - start):.3f} seconds")

        # Third order - with nonce
        start = time.time()
        address = web3.to_checksum_address(USER_ADDRESS)
        nonce = web3.eth.get_transaction_count(address)
        tx_options_with_nonce = TxOptions(
            gas_limit=140000,
            gas_price=1000000000,
            max_priority_fee_per_gas=0,
            nonce=nonce
        )
        tx_hash3 = await order_executor.place_order(order, "order_3", tx_options_with_nonce)
        event3 = await order_executor.order_created_channel.get()
        print(f"Order 3 (TX options with nonce) total time: {(time.time() - start):.3f} seconds")

    finally:
        await order_executor.disconnect()

if __name__ == "__main__":
    asyncio.run(place_single_order()) 