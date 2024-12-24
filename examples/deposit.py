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
WS_URL = "https://ws.staging.kuru.io"

async def main():
    client = KuruClient(
        network_rpc=NETWORK_RPC,
        margin_account_address=ADDRESSES['margin_account'],
        websocket_url=WS_URL,
        private_key=os.getenv('PK')
    )
    
    # Deposit 100 USDC
    client.deposit(ADDRESSES['usdc'], 100000000000000000000000)

    print(await client.view_margin_balance(ADDRESSES['usdc']))

    ## Deposit 100 WBT
    # await client.deposit(ADDRESSES['wbtc'], 10000000000000)

    # Withdraw 100 USDC
    # client.withdraw(ADDRESSES['usdc'], 100000000000000000000000)

if __name__ == "__main__":
    asyncio.run(main())
