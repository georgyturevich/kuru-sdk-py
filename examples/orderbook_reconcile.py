import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from web3 import Web3

from kuru_sdk.order_executor import OrderRequest
from kuru_sdk.orderbook import Orderbook
from kuru_sdk.client import KuruClient

import os

ADDRESSES = {
    'margin_account': '0x33fa695D1B81b88638eEB0a1d69547Ca805b8949',
    'orderbook': '0x3a4cc34d6cc8b5e8aeb5083575aaa27f2a0a184a',
    'usdc': '0x9A29e9Bab1f0B599d1c6C39b60a79596b3875f56',
    'wbtc': '0x0000000000000000000000000000000000000000'
}

class OrderbookState:
  def __init__(self):
    self.l2_book = None

async def main():

  web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

  market_address = ADDRESSES['orderbook']

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


def generate_random_orders(market_address: str, num_orders: int):
  orders = []
  for i in range(num_orders):
    order = OrderRequest(
      market_address=market_address,
      order_type="limit",
      side="buy",
      size=0.1,
      price=0.88,
      post_only=False,
      cloid=f"mm-{i}"
    )
    orders.append(order)

  return orders
    
if __name__ == "__main__":
  asyncio.run(main())
