# Kuru Python SDK

A Python SDK for interacting with Kuru's Central Limit Orderbook (CLOB).

## Features

- Margin Account Management
  - Deposit and withdraw tokens
- Order Management
  - Place limit and market orders
  - Cancel orders
  - Real-time order tracking via WebSocket
  - Batch orders


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
    'mon/usdc': '0x3a4cc34d6cc8b5e8aeb5083575aaa27f2a0a184a',
    'margin_account': '0x33fa695D1B81b88638eEB0a1d69547Ca805b8949',
    'usdc': '0x9A29e9Bab1f0B599d1c6C39b60a79596b3875f56',
    'mon': '0x0000000000000000000000000000000000000000'
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

### Placing single order
```python
async def main():

    # Limit buy
    order = OrderRequest(
        cloid = "mm_1"
        market_address=ADDRESSES['mon/usdc'],
        order_type='limit',
        side='buy',
        price=price,
        size=size,
        post_only=post_only
    )

    # Limit sell
    order = OrderRequest(
        cloid = "mm_2"
        market_address=ADDRESSES['mon/usdc'],
        order_type='limit',
        side='sell',
        price=price,
        size=size,
        post_only=post_only
    )

    # Market buy
    order = OrderRequest(
        cloid = "mm_3"
        market_address=ADDRESSES['mon/usdc'],
        order_type='market',
        side='buy',
        size=size,
        min_amount_out=min_amount,
        fill_or_kill=False
    )

    # Market sell
    order = OrderRequest(
        cloid = "mm_4"
        market_address=ADDRESSES['mon/usdc'],
        order_type='market',
        side='sell',
        size=size,
        min_amount_out=min_amount,
        fill_or_kill=False
    )

    try:
        tx_hash = await client.create_order(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing order: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
```

### Placing batch orders
```python
async def main():

    # Limit buy
    order1 = OrderRequest(
        cloid = "mm_5"
        market_address=ADDRESSES['mon/usdc'],
        order_type='limit',
        side='buy',
        price=price,
        size=size,
        post_only=post_only
    )

    # Limit sell
    order2 = OrderRequest(
        cloid = "mm_6"
        market_address=ADDRESSES['mon/usdc'],
        order_type='limit',
        side='sell',
        price=price,
        size=size,
        post_only=post_only
    )

    # Cancel order
    order3 = OrderRequest(
        market_address=ADDRESSES['mon/usdc'],
        order_type='cancel',
        order_ids_to_cancel=["mm_1", "mm_2"]
    )

    orders = [order1, order2, order3]

    try:
        tx_hash = await client.batch_orders(order)
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error placing batch order: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
```

### Cancelling order

```python

async def main():
    try:
        tx_hash = await client.cancel_order("mm_1")
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error cancelling order: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
```

### Batch cancelling orders

```python
async def main():
    try:
        tx_hash = await client.batch_cancel_orders(["mm_1", "mm_2"])
        print(f"Transaction hash: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error cancelling orders: {str(e)}")
        return None
```

## Components

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

### WebSocket Connection Management

The SDK handles WebSocket connections automatically, but you need to properly connect and disconnect:
The client automatically connects to ws. But it has to be manually disabled once done.

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

### Orderbook Reconciliation

The SDK provides a method to reconcile the local orderbook with the on-chain orderbook using events from the websocket. This requires you to write custom callback functions and pass it to the KuruClient.


```python
class OrderbookState:
  def __init__(self):
    self.l2_book = None

async def main():

  web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

  market_address = ADDRESSES['mon/usdc']

  orderbook = Orderbook(
    web3=web3,
    contract_address=market_address,
    private_key=os.getenv("PK")
  )

  # Create a container class to hold the l2_book state

  state = OrderbookState()
  state.l2_book = await orderbook.fetch_orderbook()
  print(state.l2_book)

  # on order created callback that reconciles the orderbook and updates l2_book
  def on_order_created(payload):
    try:
      print(f"Received order created event: {payload}")
      state.l2_book = orderbook.reconcile_orderbook(state.l2_book, "OrderCreated", payload)
      print("Updated L2Book:", state.l2_book)
    except Exception as e:
      print(f"Error reconciling order created: {e}")
      print(f"Payload: {payload}")
      # print(f"Current L2Book: {state.l2_book}")

  # on order cancelled callback that reconciles the orderbook and updates l2_book
  def on_order_cancelled(payload):
    print(f"Received order cancelled event: {payload}")
    try:
      state.l2_book = orderbook.reconcile_orderbook(state.l2_book, "OrderCancelled", payload)
      print("Updated L2Book:", state.l2_book)
    except Exception as e:
      print(f"Error reconciling order cancelled: {e}")
      print(f"Payload: {payload}")
      # print(f"Current L2Book: {state.l2_book}")

  # on trade callback that reconciles the orderbook and updates l2_book
  def on_trade(payload):
    print(f"Received trade event: {payload}")
    try:
        state.l2_book = orderbook.reconcile_orderbook(state.l2_book, "Trade", payload)
        print("Updated L2Book:", state.l2_book)
    except Exception as e:
        print(f"Error reconciling trade: {e}")
        print(f"Payload: {payload}")
        # print(f"Current L2Book: {state.l2_book}")

  client = KuruClient(
    network_rpc=os.getenv("RPC_URL"),
    margin_account_address=ADDRESSES['margin_account'],
    private_key=os.getenv("PK"),
    websocket_url=os.getenv("WS_URL"),
    on_order_created=on_order_created,
    on_order_cancelled=on_order_cancelled,
    on_trade=on_trade
  )

  orders = generate_random_orders(market_address, 2)

  for order in orders:
    await client.create_order(order)

    await asyncio.sleep(2)

    print("client.executed_trades", client.get_all_executed_trades_for_market(market_address))

  await asyncio.sleep(10)
```


# Always disconnect when done
```python
await client.disconnect()
```

