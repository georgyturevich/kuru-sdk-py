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

## Environment Variables

The SDK uses the following environment variables:

```bash
RPC_URL=your_ethereum_rpc_url
PK=your_private_key
```

## Requirements

- Python 3.7+
- web3.py
- python-socketio
- python-dotenv
- aiohttp

## Quick Start

Here's an example for depositing to the margin account. User needs margin account balance for limit orders.

Note: The deposit amount is in wei

```python
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from web3 import Web3
from kuru_sdk.margin import MarginAccount
import os
import json
import argparse

from dotenv import load_dotenv

load_dotenv()

from kuru_sdk.client import KuruClient

# Network and contract configuration
NETWORK_RPC = os.getenv("RPC_URL")  # Replace with your network RPC
ADDRESSES = {
    'margin_account': '0x33fa695D1B81b88638eEB0a1d69547Ca805b8949',
    'usdc': '0x9A29e9Bab1f0B599d1c6C39b60a79596b3875f56',
    'wbtc': '0x0000000000000000000000000000000000000000'
}

async def main():
    client = KuruClient(
        network_rpc=NETWORK_RPC,
        margin_account_address=ADDRESSES['margin_account'],
        private_key=os.getenv('PK')
    )
    
    # Deposit 100 USDC
    await client.deposit(ADDRESSES['usdc'], 100000000000000000000000)

    print(await client.view_margin_balance(ADDRESSES['usdc']))


if __name__ == "__main__":
    asyncio.run(main())

```

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
async def place_limit_buy(client: KuruClient, price: str, size: str, post_only: bool = False, tx_options: TxOptions = TxOptions()):
    """Place a limit buy order"""

    print(f"Placing limit buy order: {size} units at {price}")

    order = OrderRequest(
        cloid = "mm_1"
        market_address=ADDRESSES['orderbook'],
        order_type='limit',
        side='buy',
        price=price,
        size=size,
        post_only=post_only
    )
    try:
        print(f"Placing limit buy order: {size} units at {price}")
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing limit buy order: {str(e)}")
        return None

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

By using `TxOptions` tou can save 1-2 seconds in runtime.

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

client = KuruClient(
    network_rpc='RPC_URL',
    margin_account_address='MARGIN_ACCOUNT_ADDRESS',
    websocket_url='WS_URL',
    private_key='PRIVATE_KEY'
    on_order_created=on_order_created
    on_trade=on_trade
    on_order_cancelled=on_order_cancelled
)
```

### WebSocket Connection Management

The SDK handles WebSocket connections automatically, but you need to properly connect and disconnect:
The client automatically connects to ws. But it has to be manually disabled

```python
# Always disconnect when done
await client.disconnect()
```

