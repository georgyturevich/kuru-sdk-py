import pytest
from web3 import Web3
from decimal import Decimal
import asyncio
from typing import Tuple

from src.orderbook import Orderbook
from src.margin import MarginAccount

# Test addresses - replace with your test addresses
TESTING_ADDRESSES = {
    'margin_account_address': '0x8A791620dd6260079BF849Dc5567aDC3F2FdC318',
    'wbtc_address': '0x5FbDB2315678afecb367f032d93F642f64180aa3',
    'usdc_address': '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512',
    'orderbook_address': '0x29BdC6fc3Bb87fb461Bd41DBc50f9097123f6aef'
}

# Standard ERC20 ABI for basic functions we need
ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

async def setup() -> Tuple[Web3, str]:
    """Setup web3 and signer for tests"""
    # Replace with your test network setup
    web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
    
    # Get test private key - in practice, use environment variables
    private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" # hardhat private key
    
    return web3, private_key

@pytest.fixture
async def test_setup():
    """Fixture to setup test environment"""
    web3, private_key = await setup()
    account = web3.eth.account.from_key(private_key)
    
    # Initialize contracts
    margin_account = MarginAccount(
        web3=web3,
        contract_address=TESTING_ADDRESSES['margin_account_address'],
        private_key=private_key
    )
    
    # Initialize ERC20 contract interfaces
    wbtc_contract = web3.eth.contract(
        address=Web3.to_checksum_address(TESTING_ADDRESSES['wbtc_address']),
        abi=ERC20_ABI
    )
    
    usdc_contract = web3.eth.contract(
        address=Web3.to_checksum_address(TESTING_ADDRESSES['usdc_address']),
        abi=ERC20_ABI
    )
    
    orderbook = Orderbook(
        web3=web3,
        contract_address=TESTING_ADDRESSES['orderbook_address'],
        private_key=private_key
    )
    
    return {
        'web3': web3,
        'account': account,
        'margin_account': margin_account,
        'wbtc_contract': wbtc_contract,
        'usdc_contract': usdc_contract,
        'orderbook': orderbook
    }

@pytest.mark.asyncio
async def test_market_buy(test_setup):
    """Test market buy order"""
    setup_data = await test_setup
    web3 = setup_data['web3']
    account = setup_data['account']
    margin_account = setup_data['margin_account']
    wbtc_contract = setup_data['wbtc_contract']
    usdc_contract = setup_data['usdc_contract']
    orderbook = setup_data['orderbook']
    
    # Calculate deposit amount
    amount = 100000000 * (10 ** 25)
    
    # Approve usdc to margin account
    balance = usdc_contract.functions.balanceOf(account.address).call()
    print(f"USDC Balance before deposit: {balance}")
    
    tx = usdc_contract.functions.approve(
        margin_account.contract_address,
        amount
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
    })
    
    # Sign and send the transaction, wait for receipt
    signed_tx = web3.eth.account.sign_transaction(tx, account.key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"Transaction receipt: {receipt}")

    # # Deposit to margin account
    print(f"Margin Account Contract Address: {margin_account.contract_address}")
    margin_account.deposit(
        user=account.address,
        token=TESTING_ADDRESSES['usdc_address'],
        amount=amount,
        from_address=account.address
    )
    # await margin_account.deposit(
    #     user=account.address,
    #     token=TESTING_ADDRESSES['wbtc_address'],
    #     amount=amount,
    #     from_address=account.address
    # )
    
    # # Get initial balance
    # usdc_balance_before = await usdc_contract.functions.balanceOf(account.address).call()
    # print(f"USDC balance before: {usdc_balance_before}")
    
    # # Approve orderbook
    # tx = await wbtc_contract.functions.approve(
    #     orderbook.contract_address,
    #     amount
    # ).build_transaction({
    #     'from': account.address,
    #     'nonce': web3.eth.get_transaction_count(account.address),
    # })
    
    # signed_tx = web3.eth.account.sign_transaction(tx, account.key)
    # tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    # await web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # # Execute market buy
    # tx_hash = await orderbook.market_buy(
    #     size="2",
    #     min_amount_out="0",
    #     is_margin=True,
    #     fill_or_kill=False
    # )
    # print(f"Transaction hash: {tx_hash}")
    
    # # Get final balance
    # usdc_balance_after = await usdc_contract.functions.balanceOf(account.address).call()
    # print(f"USDC balance after: {usdc_balance_after}")

# @pytest.mark.asyncio
# async def test_market_sell(test_setup):
#     """Test market sell order"""
#     setup_data = await test_setup
#     web3 = setup_data['web3']
#     account = setup_data['account']
#     margin_account = setup_data['margin_account']
#     wbtc_contract = setup_data['wbtc_contract']
#     usdc_contract = setup_data['usdc_contract']
#     orderbook = setup_data['orderbook']
    
#     # Calculate deposit amount
#     amount = 1000 * (10 ** 25)
    
#     # Deposit to margin account
#     await margin_account.deposit(
#         user=account.address,
#         token=TESTING_ADDRESSES['usdc_address'],
#         amount=amount,
#         from_address=account.address
#     )
#     await margin_account.deposit(
#         user=account.address,
#         token=TESTING_ADDRESSES['wbtc_address'],
#         amount=amount,
#         from_address=account.address
#     )
    
#     # Get initial balance
#     usdc_balance_before = await usdc_contract.functions.balanceOf(account.address).call()
#     print(f"USDC balance before: {usdc_balance_before}")
    
#     # Approve orderbook
#     tx = await wbtc_contract.functions.approve(
#         orderbook.contract_address,
#         amount
#     ).build_transaction({
#         'from': account.address,
#         'nonce': web3.eth.get_transaction_count(account.address),
#     })
    
#     signed_tx = web3.eth.account.sign_transaction(tx, account.key)
#     tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
#     await web3.eth.wait_for_transaction_receipt(tx_hash)
    
#     # Execute market sell
#     tx_hash = await orderbook.market_sell(
#         size="1",
#         min_amount_out="0",
#         is_margin=True,
#         fill_or_kill=False
#     )
#     print(f"Transaction hash: {tx_hash}")
    
#     # Get final balance
#     usdc_balance_after = await usdc_contract.functions.balanceOf(account.address).call()
#     print(f"USDC balance after: {usdc_balance_after}")

# @pytest.mark.asyncio
# async def test_limit_buy(test_setup):
#     """Test limit buy order"""
#     setup_data = await test_setup
#     web3 = setup_data['web3']
#     account = setup_data['account']
#     margin_account = setup_data['margin_account']
#     wbtc_contract = setup_data['wbtc_contract']
#     usdc_contract = setup_data['usdc_contract']
#     orderbook = setup_data['orderbook']
    
#     # Calculate amount
#     amount = 100000000 * (10 ** 18)
    
#     # Get initial balance
#     usdc_balance_before = await usdc_contract.functions.balanceOf(account.address).call()
#     print(f"USDC balance before: {usdc_balance_before}")
    
#     # Approve orderbook
#     tx = await wbtc_contract.functions.approve(
#         orderbook.contract_address,
#         amount
#     ).build_transaction({
#         'from': account.address,
#         'nonce': web3.eth.get_transaction_count(account.address),
#     })
    
#     signed_tx = web3.eth.account.sign_transaction(tx, account.key)
#     tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
#     await web3.eth.wait_for_transaction_receipt(tx_hash)
    
#     # Place limit buy order
#     tx_hash, order_id = await orderbook.add_buy_order(
#         price="259",
#         size="1",
#         post_only=False
#     )
#     print(f"Transaction hash: {tx_hash}")
#     print(f"Order ID: {order_id}")
    
#     # Get final balance
#     usdc_balance_after = await usdc_contract.functions.balanceOf(account.address).call()
#     print(f"USDC balance after: {usdc_balance_after}")

# @pytest.mark.asyncio
# async def test_limit_sell(test_setup):
#     """Test limit sell order"""
#     setup_data = await test_setup
#     web3 = setup_data['web3']
#     account = setup_data['account']
#     margin_account = setup_data['margin_account']
#     wbtc_contract = setup_data['wbtc_contract']
#     usdc_contract = setup_data['usdc_contract']
#     orderbook = setup_data['orderbook']
    
#     # Calculate amount
#     amount = 100000000 * (10 ** 18)
    
#     # Deposit to margin account
#     await margin_account.deposit(
#         user=account.address,
#         token=TESTING_ADDRESSES['usdc_address'],
#         amount=amount,
#         from_address=account.address
#     )
#     await margin_account.deposit(
#         user=account.address,
#         token=TESTING_ADDRESSES['wbtc_address'],
#         amount=amount,
#         from_address=account.address
#     )
    
#     # Get initial balance
#     usdc_balance_before = await usdc_contract.functions.balanceOf(account.address).call()
#     print(f"USDC balance before: {usdc_balance_before}")
    
#     # Approve orderbook
#     tx = await wbtc_contract.functions.approve(
#         orderbook.contract_address,
#         amount
#     ).build_transaction({
#         'from': account.address,
#         'nonce': web3.eth.get_transaction_count(account.address),
#     })
    
#     signed_tx = web3.eth.account.sign_transaction(tx, account.key)
#     tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
#     await web3.eth.wait_for_transaction_receipt(tx_hash)
    
#     # Execute market sell (as in the Rust test)
#     tx_hash = await orderbook.market_sell(
#         size="100",
#         min_amount_out="0",
#         is_margin=True,
#         fill_or_kill=False
#     )
#     print(f"Transaction hash: {tx_hash}")
    
#     # Get final balance
#     usdc_balance_after = await usdc_contract.functions.balanceOf(account.address).call()
#     print(f"USDC balance after: {usdc_balance_after}")

if __name__ == "__main__":
    pytest.main([__file__])