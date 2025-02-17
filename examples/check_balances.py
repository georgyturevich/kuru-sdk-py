import sys
from pathlib import Path
from typing import Dict, Tuple
import asyncio

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from web3 import Web3
from kuru_sdk.token import Token
from kuru_sdk.margin import MarginAccount
import os
import argparse
from decimal import Decimal
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()

# Network and contract configuration
NETWORK_RPC = os.getenv("RPC_URL")

# Contract addresses
ADDRESSES = {
    'margin_account': '0x4B186949F31FCA0aD08497Df9169a6bEbF0e26ef',
    'CHOG': '0x7E9953A11E606187be268C3A6Ba5f36635149C81',
    'MON': '0x0000000000000000000000000000000000000000'
}

def get_address_from_private_key(private_key: str) -> str:
    """
    Get Ethereum address from private key
    
    Args:
        private_key: Private key in hex format
        
    Returns:
        str: Ethereum address
    """
    if private_key.startswith('0x'):
        private_key = private_key[2:]
    account = Account.from_key(private_key)
    return account.address

async def check_balances(address: str) -> Tuple[Dict[str, Decimal], Dict[str, Decimal]]:
    """
    Check wallet and margin account balances for a given address
    
    Args:
        address: Address to check balances for
        
    Returns:
        Tuple[Dict[str, Decimal], Dict[str, Decimal]]: Wallet balances and margin balances
    """
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    address = Web3.to_checksum_address(address)
    
    wallet_balances = {}
    margin_balances = {}
    
    # Initialize margin account
    margin_account = MarginAccount(
        web3=web3,
        contract_address=ADDRESSES['margin_account']
    )
    
    # Get MON (native token) balances
    eth_balance = web3.eth.get_balance(address)
    wallet_balances['MON'] = Decimal(eth_balance) / Decimal(1e18)
    
    margin_mon_balance = await margin_account.get_balance(address, ADDRESSES['MON'])
    margin_balances['MON'] = Decimal(margin_mon_balance) / Decimal(1e18)
    
    # Get CHOG balances
    token = Token(web3, ADDRESSES['CHOG'])
    
    # Wallet balance
    raw_balance = token.balance_of(address)
    wallet_balances['CHOG'] = token.format_units(raw_balance)
    
    # Margin balance
    raw_margin_balance = await margin_account.get_balance(address, ADDRESSES['CHOG'])
    margin_balances['CHOG'] = token.format_units(raw_margin_balance)
        
    return wallet_balances, margin_balances

async def main():
    parser = argparse.ArgumentParser(description='Check token balances for an address')
    parser.add_argument('--address', help='Address to check balances for (optional, uses PK from .env if not provided)')
    
    args = parser.parse_args()
    
    try:
        if args.address:
            address = args.address
        else:
            private_key = os.getenv('PK')
            if not private_key:
                print("Error: No address provided and PK not found in .env file")
                sys.exit(1)
            address = get_address_from_private_key(private_key)
            print(f"Using address derived from private key: {address}")
            
        wallet_balances, margin_balances = await check_balances(address)
        
        print(f"\nBalances for address: {address}")
        print("-" * 50)
        print("\nWallet Balances:")
        for token, balance in wallet_balances.items():
            print(f"{token}: {balance:,.8f}")
            
        print("\nMargin Account Balances:")
        for token, balance in margin_balances.items():
            print(f"{token}: {balance:,.8f}")
            
    except Exception as e:
        print(f"Error checking balances: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
