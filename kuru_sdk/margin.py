from web3 import Web3
from eth_typing import Address
from typing import Optional, Union, List, Dict, Any
from web3.contract import Contract
import json
import os

class MarginAccount:
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        private_key: Optional[str] = None
    ):
        """
        Initialize the MarginAccount SDK
        
        Args:
            web3: Web3 instance
            contract_address: Address of the deployed MarginAccount contract
            private_key: Private key for signing transactions (optional)
        """
        self.web3 = web3
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.private_key = private_key
        
        # Load ABI from JSON file
        with open(os.path.join(os.path.dirname(__file__), 'abi/marginaccount.json'), 'r') as f:
            contract_abi = json.load(f)
        
        self.contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=contract_abi
        )
        
        # Native token address constant
        self.NATIVE = "0x0000000000000000000000000000000000000000"

    async def deposit(
        self,
        user: str,
        token: str,
        amount: int,
        from_address: str
    ) -> str:
        """
        Deposit tokens into the margin account
        
        Args:
            user: Address of the user to credit
            token: Token address (use NATIVE for ETH)
            amount: Amount to deposit (in wei)
            from_address: Address sending the transaction
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        user = Web3.to_checksum_address(user)
        token = Web3.to_checksum_address(token)
        
        # Build transaction
        transaction = self.contract.functions.deposit(
            user,
            token,
            amount
        )
        
        # Handle ETH deposits
        value = amount if token == self.NATIVE else 0
        
        # Get gas estimate and nonce
        gas_estimate = transaction.estimate_gas({'from': from_address, 'value': value})
        nonce = self.web3.eth.get_transaction_count(from_address)
        
        # Build transaction dict
        transaction_dict = {
            'from': from_address,
            'nonce': nonce,
            'gas': gas_estimate,
            'gasPrice': self.web3.eth.gas_price,
            'value': value
        }
        
        if self.private_key:
            # Sign and send transaction
            raw_transaction = transaction.build_transaction(transaction_dict)
            signed_txn = self.web3.eth.account.sign_transaction(
                raw_transaction,
                self.private_key
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        else:
            # Let the user's wallet handle signing
            raise Exception("Private key is required to deposit tokens into the margin account")
            
        return tx_hash.hex()

    async def withdraw(
        self,
        token: str,
        amount: int,
        from_address: str
    ) -> str:
        """
        Withdraw tokens from the margin account
        
        Args:
            amount: Amount to withdraw (in wei)
            token: Token address (use NATIVE for ETH)
            from_address: Address sending the transaction
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        token = Web3.to_checksum_address(token)
        
        # Build transaction
        transaction = self.contract.functions.withdraw(
            amount,
            token
        )
        
        # Get gas estimate and nonce
        gas_estimate = transaction.estimate_gas({'from': from_address})
        nonce = self.web3.eth.get_transaction_count(from_address)
        
        # Build transaction dict
        transaction_dict = {
            'from': from_address,
            'nonce': nonce,
            'gas': gas_estimate,
            'gasPrice': self.web3.eth.gas_price
        }
        
        if self.private_key:
            # Sign and send transaction
            raw_transaction = transaction.build_transaction(transaction_dict)
            signed_txn = self.web3.eth.account.sign_transaction(
                raw_transaction,
                self.private_key
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        else:
            raise Exception("Private key is required to withdraw tokens from the margin account")
            
        return tx_hash.hex()
    
    async def get_balance(
        self,
        user: str,
        token: str
    ) -> int:
        return self.contract.functions.getBalance(user, token).call()

__all__ = ['MarginAccount']