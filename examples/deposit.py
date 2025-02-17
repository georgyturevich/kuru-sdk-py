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
    'margin_account': '0x4B186949F31FCA0aD08497Df9169a6bEbF0e26ef',
    'chog': '0x7E9953A11E606187be268C3A6Ba5f36635149C81',
    'mon': '0x0000000000000000000000000000000000000000'
}
WS_URL = "https://ws.testnet.kuru.io"

async def main():
    client = KuruClient(
        network_rpc=NETWORK_RPC,
        margin_account_address=ADDRESSES['margin_account'],
        websocket_url=WS_URL,
        private_key=os.getenv('PK')
    )
    
    # Deposit 100 USDC
    await client.deposit(ADDRESSES['mon'], 5000000000000000000)


    print(await client.view_margin_balance(ADDRESSES['mon']))

    ## Deposit 100 WBT
    # await client.deposit(ADDRESSES['wbtc'], 10000000000000)

    # Withdraw 100 USDC
    # client.withdraw(ADDRESSES['usdc'], 100000000000000000000000)

if __name__ == "__main__":
    asyncio.run(main())
