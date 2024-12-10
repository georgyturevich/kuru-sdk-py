import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)


import asyncio
import random
from decimal import Decimal
from web3 import Web3
from src.order_executor import OrderExecutor, OrderRequest
from src.margin import MarginAccount

# Use the same configuration as in orders.py
NETWORK_RPC = "https://devnet1.monad.xyz/rpc/WbScX50z7Xsvsuk6UB1uMci8Ekee3PJqhBZ2RRx0xSjyqx9hjipbfMh60vr7a1gS"  # Local network
ADDRESSES = {
    'orderbook': '0x336bd8b100d572cb3b4af481ace50922420e6d1b',
    'margin': '0x67da6CA8F829a7A51701Eb3dB2296d349fBC3832',
    'usdc': '0x34084eAEbe9Cbc209A85FFe22fa387223CDFB3e8',
    'wbtc': '0xf4f7ca3c361cA2B457Ca6AC9E393B2dad5C6b78b'
}

with open('abi/ierc20.json', 'r') as file:
    ERC20_ABI = json.load(file)

async def test_order_executor():
    # Initialize Web3 and OrderExecutor
    web3 = Web3(Web3.HTTPProvider(NETWORK_RPC))
    contract_address = ADDRESSES['orderbook']
    websocket_url = "https://ws.staging.kuru.io"  # Make sure this is the correct WebSocket URL
    private_key = "0xa31d0eeff3db5f7b7872ebe47123caab84273952dc80021ae2a388c60d6ea9fc"  # Local test private key

    account = web3.eth.account.from_key(private_key)

    amount = web3.to_wei(500, 'ether')  # 1000 * 1e18

    # Initialize MarginAccount
    margin_account = MarginAccount(
        web3=web3,
        contract_address=ADDRESSES['margin'],
        private_key=private_key
    )

    token_address = ADDRESSES['usdc']
    token_contract = web3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=ERC20_ABI
    )

    tx = token_contract.functions.approve(
        margin_account.contract_address,
        amount
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
    })

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Approve transaction hash: {tx_hash.hex()}")

    # await asyncio.sleep(2)

    margin_deposit_tx_hash = margin_account.deposit(
        user=account.address,
        token=token_address,
        amount=amount,
        from_address=account.address
    )
    print(f"Margin deposit transaction hash: {margin_deposit_tx_hash}")

    await asyncio.sleep(2)

    # # Deposit wbtc to margin account
    # token_address = ADDRESSES['wbtc']
    # token_contract = web3.eth.contract(
    #     address=Web3.to_checksum_address(token_address),
    #     abi=ERC20_ABI
    # )

    # amount = web3.to_wei(1000, 'ether')  # 1 * 1e18 

    # tx = token_contract.functions.approve(
    #     margin_account.contract_address,
    #     amount
    # ).build_transaction({
    #     'from': account.address,
    #     'nonce': web3.eth.get_transaction_count(account.address),
    # })

    # signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    # tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    # print(f"Approve transaction hash: {tx_hash.hex()}")

    # await asyncio.sleep(2)

    # margin_account.deposit(
    #     user=account.address,
    #     token=token_address,
    #     amount=amount,
    #     from_address=account.address
    # )

    await asyncio.sleep(2)


    order_executor = OrderExecutor(
        web3=web3,
        contract_address=contract_address,
        websocket_url=websocket_url,
        private_key=private_key
    )

    # Connect to WebSocket
    await order_executor.connect()

    try:
        for i in range(2):
            print(f"Placing order {i+1}/10:")
            # Generate random order parameters
            order_type = random.choice(["limit", "market"])
            side = random.choice(["buy", "sell"])
            
            # Random price between 100 and 1000
            price = str(Decimal(random.uniform(1, 10)).quantize(Decimal('0.01')))
            
            # Random size between 0.1 and 10
            size = str(Decimal(random.uniform(0.01, 5)).quantize(Decimal('0.001')))
            
            # Random boolean flags
            post_only = random.choice([True, False])
            is_margin = random.choice([True, False])
            fill_or_kill = random.choice([True, False])
            
            # For market orders, set min_amount_out as 80% of size
            min_amount_out = str(Decimal(size) * Decimal('0.8')) if order_type == "market" else None

            # Create order request
            # order = OrderRequest(
            #     order_type=order_type,
            #     side=side,
            #     price=price if order_type == "limit" else None,
            #     size=size,
            #     post_only=post_only,
            #     is_margin=is_margin,
            #     fill_or_kill=fill_or_kill,
            #     min_amount_out=min_amount_out
            # )

            order = OrderRequest(
                order_type="limit",
                side="buy",
                price="177.4",
                size="1",
                post_only=False
            )

            # Generate a unique client order ID (CLOID)
            cloid = f"order_{i}_{random.randint(1000, 9999)}"

            try:
                print(f"\nPlacing order {i+1}/2:")
                print(f"CLOID: {cloid}")
                print(f"Type: {order_type}")
                print(f"Side: {side}")
                print(f"Price: {price if order_type == 'limit' else 'N/A'}")
                print(f"Size: {size}")
                print(f"Min Amount Out: {min_amount_out if order_type == 'market' else 'N/A'}")

                # Place the order
                tx_hash = await order_executor.place_order(order, cloid)
                print(f"Transaction hash: {tx_hash}")

                # Wait for order confirmation
                # You might want to adjust the sleep time based on your network
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Error placing order {i+1}: {str(e)}")

            await asyncio.sleep(1)


    finally:
        print("order_executor.cloid_to_order: ", order_executor.cloid_to_order)
        print("order_executor.executed_trades: ", order_executor.executed_trades)
        print("order_executor.cancelled_orders: ", order_executor.cancelled_orders)
        await order_executor.disconnect()

# Run the script
if __name__ == "__main__":
    asyncio.run(test_order_executor())
