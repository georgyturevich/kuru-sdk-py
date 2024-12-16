import os
import random
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

import asyncio
import json
from decimal import Decimal
from typing import Optional
import aiohttp
from web3 import Web3

from dotenv import load_dotenv

load_dotenv()

from kuru_sdk.client import KuruClient
from kuru_sdk.order_executor import OrderRequest

class MarketMaker:
    def __init__(
        self,
        network_rpc: str,
        margin_account_address: str,
        private_key: str,
        market_address: str,
        base_size: Decimal = Decimal("1.0"),
        spread_bps: Decimal = Decimal("10"),  # 0.1% spread
    ):
        self.client = KuruClient(
            network_rpc=network_rpc,
            margin_account_address=margin_account_address,
            websocket_url=os.getenv("WS_URL"),
            private_key=private_key,
            on_order_created=self.on_order_created,
            on_trade=self.on_trade,
            on_order_cancelled=self.on_order_cancelled
        )
        self.market_address = market_address
        self.base_size = base_size
        self.spread_bps = spread_bps
        self.active_orders = set()
        self.cloid_counter = 0

    def _generate_cloid(self) -> str:
        """Generate a unique client order ID"""
        self.cloid_counter += 1
        return f"mm_{self.cloid_counter}"

    async def on_order_created(self, event):
        print(f"Order created: {event}")

    async def on_trade(self, event):
        print(f"Trade executed: {event}")

    async def on_order_cancelled(self, event):
        print(f"Order cancelled: {event}")

    async def get_binance_price(self) -> Decimal:
        """Fetch current SOL price from Binance"""
        url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                # price = 1 + random.uniform(-0.005, 0.005)
                # return Decimal(price)
                return Decimal(data["price"])
            

    async def update_orders(self):
        """Update market making orders based on current price"""
        try:
            # Get current market price
            base_price = await self.get_binance_price()
            print(f"base_price: {base_price}")
            spread = base_price * (self.spread_bps / Decimal("10000"))
            
            # Calculate bid and ask prices
            bid_price = str(Decimal(str(round(base_price - spread, 2))))
            ask_price = str(Decimal(str(round(base_price + spread, 2))))
            size = str(self.base_size)

            # Create buy order
            buy_order = OrderRequest(
                market_address=self.market_address,
                order_type="limit",
                side="buy",
                price=bid_price,
                size=size,
                post_only=False
            )

            print(f"buy_order: {buy_order}")
            
            # Create sell order
            sell_order = OrderRequest(
                market_address=self.market_address,
                order_type="limit",
                side="sell",
                price=ask_price,
                size=size,
                post_only=False
            )

            print(f"sell_order: {sell_order}")

            # Place orders
            buy_cloid = self._generate_cloid()
            sell_cloid = self._generate_cloid()

            await self.client.create_order(buy_order, buy_cloid)
            await self.client.create_order(sell_order, sell_cloid)
            
            # Track new orders
            self.active_orders.add(buy_cloid)
            self.active_orders.add(sell_cloid)

        except Exception as e:
            print(f"Error updating orders: {e}")

    async def start(self):
        """Start the market making bot"""
        try:
            while True:
                await self.update_orders()
                await asyncio.sleep(6)  # Update every 6 seconds

        except KeyboardInterrupt:
            print("Shutting down market maker...")
        except Exception as e:
            print(f"Error in market maker: {e}")


# Example usage:
async def main():
    network_rpc = os.getenv("RPC_URL")
    margin_account_address = "0x33fa695D1B81b88638eEB0a1d69547Ca805b8949"
    market_address = "0x3a4cc34d6cc8b5e8aeb5083575aaa27f2a0a184a"
    private_key = os.getenv("PK")

    market_maker = MarketMaker(
        network_rpc=network_rpc,
        margin_account_address=margin_account_address,
        private_key=private_key,
        market_address=market_address,
        base_size=Decimal("0.1"),  # 0.1 SOL per order
        spread_bps=Decimal("100")   # 1% spread
    )

    await market_maker.start()

if __name__ == "__main__":
    asyncio.run(main())