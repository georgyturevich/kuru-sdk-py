import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from web3 import Web3
from src.margin import MarginAccount
import os
import json
import argparse

# Network and contract configuration
NETWORK_RPC = "http://localhost:8545"  # Replace with your network RPC
ADDRESSES = {
    'margin_account': '0x8A791620dd6260079BF849Dc5567aDC3F2FdC318',
    'usdc': '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512',
    'wbtc': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
}

# Load ERC20 ABI from JSON file
with open('abi/ierc20.json', 'r') as f:
    ERC20_ABI = json.load(f)

def deposit(token_symbol: str, amount: int):
    """
    Deposit tokens into the margin account
    
    Args:
        token_symbol: 'usdc' or 'wbtc'
        amount: Amount to deposit (in wei)
    """
    # Initialize Web3
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    
    # Get private key from environment (safer than hardcoding)
    private_key = os.getenv('PRIVATE_KEY', "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    account = web3.eth.account.from_key(private_key)
    
    # Initialize MarginAccount
    margin_account = MarginAccount(
        web3=web3,
        contract_address=ADDRESSES['margin_account'],
        private_key=private_key
    )
    
    # Initialize token contract
    token_address = ADDRESSES[token_symbol.lower()]
    token_contract = web3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=ERC20_ABI
    )
    
    try:
        # First approve the margin account to spend tokens
        print(f"Approving margin account to spend {token_symbol.upper()}...")
        tx = token_contract.functions.approve(
            margin_account.contract_address,
            amount
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
        })
        
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Approval transaction hash: {receipt.transactionHash.hex()}")
        
        # Then deposit to margin account
        print(f"Depositing {amount} {token_symbol.upper()} to margin account...")
        tx_hash = margin_account.deposit(
            user=account.address,
            token=token_address,
            amount=amount,
            from_address=account.address
        )
        print(f"Deposit transaction hash: {tx_hash}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")

def withdraw(token_symbol: str, amount: int):
    """
    Withdraw tokens from the margin account
    
    Args:
        token_symbol: 'usdc' or 'wbtc'
        amount: Amount to withdraw (in wei)
    """
    # Initialize Web3
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    
    # Get private key from environment (safer than hardcoding)
    private_key = os.getenv('PRIVATE_KEY', "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    account = web3.eth.account.from_key(private_key)
    
    # Initialize MarginAccount
    margin_account = MarginAccount(
        web3=web3,
        contract_address=ADDRESSES['margin_account'],
        private_key=private_key
    )
    
    token_address = ADDRESSES[token_symbol.lower()]
    
    try:
        print(f"Withdrawing {amount} {token_symbol.upper()} from margin account...")
        tx_hash = margin_account.withdraw(
            amount=amount,
            token=token_address,
            from_address=account.address
        )
        print(f"Withdrawal transaction hash: {tx_hash}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Deposit or withdraw tokens from margin account')
    parser.add_argument('action', choices=['deposit', 'withdraw'], help='Action to perform')
    parser.add_argument('token', choices=['usdc', 'wbtc'], help='Token to deposit/withdraw')
    parser.add_argument('amount', type=int, help='Amount in wei')
    
    args = parser.parse_args()
    
    if args.action == 'deposit':
        deposit(args.token, args.amount)
    else:
        withdraw(args.token, args.amount)

if __name__ == "__main__":
    main()
