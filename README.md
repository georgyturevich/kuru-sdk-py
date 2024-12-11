# Kuru Python SDK

A Python SDK for interacting with Kuru Protocol's decentralized exchange and margin trading platform.

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

## Quick Start

```python
from web3 import Web3
from kuru_sdk import MarginAccount, Orderbook, OrderExecutor
from kuru_sdk.orderbook import OrderRequest, TxOptions

# Initialize Web3
web3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL'))

# Initialize SDK components
margin = MarginAccount(
    web3=web3,
    contract_address='MARGIN_CONTRACT_ADDRESS',
    private_key='YOUR_PRIVATE_KEY'  # Optional
)

orderbook = Orderbook(
    web3=web3,
    contract_address='ORDERBOOK_CONTRACT_ADDRESS',
    private_key='YOUR_PRIVATE_KEY'  # Optional
)

# Example: Deposit tokens
tx_hash = margin.deposit(
    user='USER_ADDRESS',
    token='TOKEN_ADDRESS',  # Use NATIVE for ETH
    amount=1000000000000000000,  # 1 ETH in wei
    from_address='FROM_ADDRESS'
)

# Example: Place a limit buy order
order = OrderRequest(
    order_type="limit",
    side="buy",
    price="1000.5",
    size="0.1",
    post_only=True
)

executor = OrderExecutor(
    web3=web3,
    contract_address='ORDERBOOK_CONTRACT_ADDRESS',
    websocket_url='WS_URL',
    private_key='YOUR_PRIVATE_KEY'  # Optional
)

await executor.connect()
tx_hash = await executor.place_order(order, "client_order_id")
```

## Components

### MarginAccount

The `MarginAccount` class provides methods for managing collateral and margin positions:

- `deposit(user, token, amount, from_address)`: Deposit tokens into the margin account
- `withdraw(amount, token, from_address)`: Withdraw tokens from the margin account

### Orderbook

The `Orderbook` class handles order placement and management:

- Limit Orders: `add_buy_order()`, `add_sell_order()`
- Market Orders: `market_buy()`, `market_sell()`
- Order Cancellation: `batch_cancel_orders()`

### OrderExecutor

The `OrderExecutor` class provides real-time order tracking and execution:

- WebSocket connection for real-time updates
- Event handling for order creation, trades, and cancellations
- Client order ID (CLOID) tracking
- Automatic order status management

## Market Parameters

The SDK automatically handles:
- Price and size precision
- Tick size
- Minimum and maximum order sizes
- Maker and taker fees

## Error Handling

The SDK includes comprehensive error handling for:
- Normalization errors
- Gas price issues
- Transaction failures
- WebSocket connection problems

## Advanced Usage

### Setting Transaction Options

```python
tx_options = TxOptions(
    gas_limit=200000,
    gas_price=20000000000,  # 20 gwei
    max_priority_fee_per_gas=2000000000,  # 2 gwei
    nonce=None  # Auto-calculated if None
)

# Use tx_options in any transaction
await orderbook.add_buy_order(
    price="1000.5",
    size="0.1",
    post_only=True,
    tx_options=tx_options
)
```

### Event Handling

```python
async def on_order_created(event):
    print(f"Order created: {event.orderId}")

async def on_trade(event):
    print(f"Trade executed: {event.filledSize} @ {event.price}")

executor = OrderExecutor(
    web3=web3,
    contract_address='CONTRACT_ADDRESS',
    websocket_url='WS_URL',
    on_order_created=on_order_created,
    on_trade=on_trade
)


```
