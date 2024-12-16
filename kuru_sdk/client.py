
import os
import json
import argparse
import sys
from pathlib import Path

from kuru_sdk.orderbook import TxOptions

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from typing import Dict, List, Optional, Literal, Callable
from dataclasses import dataclass
from web3 import Web3
from kuru_sdk.margin import MarginAccount
from kuru_sdk.order_executor import OrderExecutor, OrderRequest

from dotenv import load_dotenv

load_dotenv()


# Load ERC20 ABI from JSON file
with open('abi/ierc20.json', 'r') as f:
    ERC20_ABI = json.load(f)

class KuruClient:
  def __init__(self, network_rpc: str, 
               margin_account_address: str, 
               private_key: str, 
               on_order_created: Optional[callable] = None,
               on_trade: Optional[callable] = None,
               on_order_cancelled: Optional[callable] = None):
    
    self.web3 = Web3(Web3.HTTPProvider(network_rpc))
    self.private_key = private_key
    self.user_address = self.web3.eth.account.from_key(private_key).address
    self.margin_account = MarginAccount(self.web3, margin_account_address, private_key)
    self.erc20_abi = ERC20_ABI

    self.on_order_created = on_order_created
    self.on_trade = on_trade
    self.on_order_cancelled = on_order_cancelled

    self.cloid_to_market_address = {}
    self.order_executors = {}

  def deposit(self, token_address: str, amount: int):
    token_contract = self.web3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=self.erc20_abi
    )
    allowance = token_contract.functions.allowance(self.user_address, self.margin_account.contract_address).call()
    if allowance < amount:
      allowance_tx = token_contract.functions.approve(self.margin_account.contract_address, amount).build_transaction({
        'from': self.user_address,
        'nonce': self.web3.eth.get_transaction_count(self.user_address),
      })
      signed_tx = self.web3.eth.account.sign_transaction(allowance_tx)
      tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
      receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
      print(f"Approval transaction hash: {receipt.transactionHash.hex()}")

    deposit_tx = self.margin_account.deposit(
      user=self.user_address,
      token=token_address,
      amount=amount,
      from_address=self.user_address
    )

    print(f"Deposit transaction hash: {deposit_tx}")

  def create_order(self, order_request: OrderRequest, cloid: str, tx_options: Optional[TxOptions] = TxOptions()):
    market_address = order_request.market_address

    if market_address not in self.order_executors:
      self.order_executors[market_address] = OrderExecutor(self.web3, self.margin_account.contract_address, self.private_key, self.on_order_created, self.on_trade, self.on_order_cancelled)

    order_executor = self.order_executors[market_address]
    try:
      tx_hash = order_executor.place_order(order_request, cloid, tx_options)
      print(f"Order placed successfully with transaction hash: {tx_hash}")
      self.cloid_to_market_address[cloid] = market_address
    except Exception as e:
      print(f"Error placing order: {e}")

  def cancel_order(self, cloid: str):
    market_address = self.cloid_to_market_address[cloid]
    self.order_executors[market_address].batch_cancel_orders([cloid])

  def batch_cancel_orders(self, market_address: str, cloids: List[str]):
    self.order_executors[market_address].batch_cancel_orders(cloids)

  def withdraw(self, token_address: str, amount: int):
    self.margin_account.withdraw(token_address, amount, self.user_address)
