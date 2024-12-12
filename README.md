# Kuru Python SDK

A Python SDK for interacting with Kuru's Central Limit Orderbook (CLOB).

## Features

- Margin Account Management
  - Deposit and withdraw tokens
  - Manage collateral
- Order Management
  - Place limit and market orders
  - Real-time order tracking via WebSocket
  - Batch order cancellation
- Advanced Trading Features
  - Post-only orders
  - Fill-or-kill orders
  - Margin trading support
  - Market making utilities

## Installation

```bash
pip install kuru-sdk
```

## Requirements

- Python 3.7+
- web3.py
- python-socketio
- python-dotenv
- aiohttp

## Quick Start

Here's a complete example showing how to place orders with different transaction options:

```python
import asyncio
import os
from decimal import Decimal
from web3 import Web3
from dotenv import load_dotenv

from kuru_sdk import OrderExecutor, OrderRequest
from kuru_sdk.orderbook import TxOptions

# Load environment variables
load_dotenv()

async def place_orders():
    # Configuration
    NETWORK_RPC = os.getenv("RPC_URL")
    CONTRACT_ADDRESS = '0x336bd8b100d572cb3b4af481ace50922420e6d1b'  # orderbook address
    WEBSOCKET_URL = 'https://ws.staging.kuru.io'
    PRIVATE_KEY = os.getenv("PK")
    
    # Initialize Web3 and OrderExecutor
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    executor = OrderExecutor(
        web3=web3,
        contract_address=CONTRACT_ADDRESS,
        websocket_url=WEBSOCKET_URL,
        private_key=PRIVATE_KEY
    )

    try:
        # Connect to WebSocket
        await executor.connect()

        # Create a basic limit order
        order = OrderRequest(
            order_type="limit",
            side="buy",
            price="179.1",
            size="0.1",
            post_only=False
        )

        # Place order without TX options
        tx_hash = await executor.place_order(order, "order_1")
        event = await executor.order_created_channel.get()
        print(f"Order created with hash: {tx_hash}")

        # Place order with custom gas settings
        tx_options = TxOptions(
            gas_limit=140000,
            gas_price=1000000000,  # 1 gwei
            max_priority_fee_per_gas=0
        )
        tx_hash = await executor.place_order(order, "order_2", tx_options)
        event = await executor.order_created_channel.get()
        
    finally:
        await executor.disconnect()

if __name__ == "__main__":
    asyncio.run(place_orders())
```

## Components

### OrderExecutor

The main class for interacting with the orderbook. It handles order placement, WebSocket connections, and event tracking.

```python
executor = OrderExecutor(
    web3=web3,
    contract_address='CONTRACT_ADDRESS',
    websocket_url='WS_URL',
    private_key='PRIVATE_KEY',  # Optional
    on_order_created=None,      # Optional callback
    on_trade=None,             # Optional callback
    on_order_cancelled=None    # Optional callback
)
```

#### Order Types

```python
# Limit Order
limit_order = OrderRequest(
    order_type="limit",
    side="buy",           # or "sell"
    price="179.1",        # Price in quote currency
    size="0.1",          # Size in base currency
    post_only=False      # Whether to ensure maker order
)

# Market Order
market_order = OrderRequest(
    order_type="market",
    side="buy",           # or "sell"
    size="0.1",
    min_amount_out="170", # Minimum amount to receive
    is_margin=False,      # Whether to use margin
    fill_or_kill=True    # Whether to require complete fill
)
```

### Transaction Options

You can customize transaction parameters using `TxOptions`:

```python
# Basic gas settings
tx_options = TxOptions(
    gas_limit=140000,
    gas_price=1000000000,  # 1 gwei
    max_priority_fee_per_gas=0
)

# With custom nonce
tx_options = TxOptions(
    gas_limit=140000,
    gas_price=1000000000,
    max_priority_fee_per_gas=0,
    nonce=web3.eth.get_transaction_count(address)
)
```

### Event Handling

The SDK provides real-time order updates through WebSocket events:

```python
async def on_order_created(event):
    print(f"Order created - ID: {event.orderId}")
    print(f"Size: {event.size}, Price: {event.price}")
    print(f"Transaction: {event.transactionHash}")

async def on_trade(event):
    print(f"Trade executed for order {event.orderId}")
    print(f"Filled size: {event.filledSize} @ {event.price}")
    print(f"Maker: {event.makerAddress}")
    print(f"Taker: {event.takerAddress}")

async def on_order_cancelled(event):
    print(f"Order {event.orderId} cancelled")

executor = OrderExecutor(
    web3=web3,
    contract_address=CONTRACT_ADDRESS,
    websocket_url=WEBSOCKET_URL,
    private_key=PRIVATE_KEY,
    on_order_created=on_order_created,
    on_trade=on_trade,
    on_order_cancelled=on_order_cancelled
)
```

### WebSocket Connection Management

The SDK handles WebSocket connections automatically, but you need to properly connect and disconnect:

```python
# Connect to WebSocket
await executor.connect()

# Place orders and handle events...

# Always disconnect when done
await executor.disconnect()
```

## Environment Variables

The SDK uses the following environment variables:

```bash
RPC_URL=your_ethereum_rpc_url
PK=your_private_key
```
