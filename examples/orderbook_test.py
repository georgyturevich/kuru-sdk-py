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

from kuru_sdk.orderbook import Orderbook

web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

ADDRESSES = {
    'margin_account': '0x33fa695D1B81b88638eEB0a1d69547Ca805b8949',
    'orderbook': '0x3a4cc34d6cc8b5e8aeb5083575aaa27f2a0a184a',
    'usdc': '0x9A29e9Bab1f0B599d1c6C39b60a79596b3875f56',
    'wbtc': '0x0000000000000000000000000000000000000000'
}


orderbook = Orderbook(
    web3=web3,
    contract_address=ADDRESSES['orderbook'],
    private_key=os.getenv("PRIVATE_KEY")
)

async def main():
    print(await orderbook.fetch_orderbook())

asyncio.run(main())

