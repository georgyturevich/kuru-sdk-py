import os
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

from src.order_executor import OrderExecutor, OrderRequest, TxOptions

class MarketMaker:
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        websocket_url: str,
        private_key: str,
        base_size: Decimal = Decimal("1.0"),
        spread_bps: Decimal = Decimal("10"),  # 0.1% spread
    ):
        self.order_executor = OrderExecutor(
            web3=web3,
            contract_address=contract_address,
            websocket_url=websocket_url,
            private_key=private_key
        )
        self.base_size = base_size
        self.spread_bps = spread_bps
        self.active_orders = set()
        self.cloid_counter = 0

    def _generate_cloid(self) -> str:
        """Generate a unique client order ID"""
        self.cloid_counter += 1
        return f"mm_{self.cloid_counter}"

    async def get_binance_price(self) -> Decimal:
        """Fetch current SOL price from Binance"""
        url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return Decimal(data["price"])

    async def update_orders(self):
        """Update market making orders based on current price"""
        try:
            # Get current market price
            base_price = await self.get_binance_price()
            print(f"base_price: {base_price}")
            spread = base_price * (self.spread_bps / Decimal("10000"))
            
            # Calculate bid and ask prices
            bid_price = str(round((base_price - spread) / 100) * 100)
            ask_price = str(round((base_price + spread) / 100) * 100)
            size = str(self.base_size)

            # Create buy order
            buy_order = OrderRequest(
                order_type="limit",
                side="buy",
                price=bid_price,
                size=size,
                post_only=False
            )

            print(f"buy_order: {buy_order}")
            
            # Create sell order
            sell_order = OrderRequest(
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

            tasks = [
                self.order_executor.place_order(buy_order, buy_cloid),
                self.order_executor.place_order(sell_order, sell_cloid)
            ]

            tx_hashes = await asyncio.gather(*tasks)
            print(f"Placed orders - Buy TX: {tx_hashes[0]}, Sell TX: {tx_hashes[1]}")
            
            # Track new orders
            self.active_orders.add(buy_cloid)
            self.active_orders.add(sell_cloid)

        except Exception as e:
            print(f"Error updating orders: {e}")

    async def start(self):
        """Start the market making bot"""
        try:
            # Connect to WebSocket
            await self.order_executor.connect()
            
            # Start order update loop
            while True:
                await self.update_orders()
                await asyncio.sleep(6)  # Update every 6 seconds

        except KeyboardInterrupt:
            print("Shutting down market maker...")
        except Exception as e:
            print(f"Error in market maker: {e}")
        finally:
            await self.order_executor.disconnect()


NETWORK_RPC = os.getenv("RPC_URL")
ADDRESSES = {
    'orderbook': '0x336bd8b100d572cb3b4af481ace50922420e6d1b',
    'usdc': '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512',
    'wbtc': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
}
# Example usage:
async def main():
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    contract_address = ADDRESSES['orderbook']
    websocket_url = 'https://ws.staging.kuru.io'
    private_key = os.getenv("PK")

    market_maker = MarketMaker(
        web3=web3,
        contract_address=contract_address,
        websocket_url=websocket_url,
        private_key=private_key,
        base_size=Decimal("0.1"),  # 1 SOL per order
        spread_bps=Decimal("100")   # 1% spread
    )

    await market_maker.start()

if __name__ == "__main__":
    asyncio.run(main())