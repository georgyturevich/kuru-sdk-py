from web3 import Web3
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import json

@dataclass
class OrderPriceSize:
    price: float
    size: float

@dataclass
class L2Book:
    block_num: int
    buy_orders: List[OrderPriceSize]
    sell_orders: List[OrderPriceSize]

@dataclass
class MarketParams:
    price_precision: int
    size_precision: int
    base_asset: str
    base_asset_decimals: int
    quote_asset: str
    quote_asset_decimals: int
    tick_size: int
    min_size: int
    max_size: int
    taker_fee_bps: int
    maker_fee_bps: int

class Orderbook:
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        contract_abi: List[Dict[str, Any]],
        private_key: Optional[str] = None
    ):
        """
        Initialize the Orderbook
        
        Args:
            web3: Web3 instance
            contract_address: Address of the deployed Orderbook contract
            contract_abi: ABI of the Orderbook contract
            private_key: Private key for signing transactions (optional)
        """
        self.web3 = web3
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.private_key = private_key
        
        self.contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=contract_abi
        )
        
        # Initialize market parameters
        self.market_params = self._fetch_market_params()

    def _fetch_market_params(self) -> MarketParams:
        """Fetch market parameters from the contract"""
        params = self.contract.functions.getMarketParams().call()
        return MarketParams(
            price_precision=params[0],
            size_precision=params[1],
            base_asset=params[2],
            base_asset_decimals=params[3],
            quote_asset=params[4],
            quote_asset_decimals=params[5],
            tick_size=params[6],
            min_size=params[7],
            max_size=params[8],
            taker_fee_bps=params[9],
            maker_fee_bps=params[10]
        )

    async def _build_and_send_transaction(self, function, value: int = 0):
        """Helper method to build and send transactions"""
        from_address = self.web3.eth.account.from_key(self.private_key).address if self.private_key else None
        
        # Get gas estimate and nonce
        if from_address:
            gas_estimate = await function.estimate_gas({'from': from_address, 'value': value})
            nonce = self.web3.eth.get_transaction_count(from_address)
            
            # Build transaction dict
            transaction_dict = {
                'from': from_address,
                'nonce': nonce,
                'gas': gas_estimate,
                'gasPrice': self.web3.eth.gas_price,
                'value': value
            }
            
            # Sign and send transaction
            raw_transaction = function.build_transaction(transaction_dict)
            signed_txn = self.web3.eth.account.sign_transaction(raw_transaction, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        else:
            # Let the user's wallet handle signing
            tx_hash = await function.transact({'value': value})
            
        return tx_hash.hex()

    async def add_buy_order(self, price: int, size: int, post_only: bool = False) -> str:
        """
        Place a limit buy order
        
        Args:
            price: Price of the buy order
            size: Size of the buy order
            post_only: If True, order will only be placed if it would be a maker order
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        function = self.contract.functions.addBuyOrder(price, size, post_only)
        return await self._build_and_send_transaction(function)

    async def add_sell_order(self, price: int, size: int, post_only: bool = False) -> str:
        """
        Place a limit sell order
        
        Args:
            price: Price of the sell order
            size: Size of the sell order
            post_only: If True, order will only be placed if it would be a maker order
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        function = self.contract.functions.addSellOrder(price, size, post_only)
        return await self._build_and_send_transaction(function)

    async def place_market_buy(
        self, 
        quote_size: int, 
        min_amount_out: int,
        use_margin: bool = False,
        fill_or_kill: bool = False
    ) -> str:
        """
        Place a market buy order
        
        Args:
            quote_size: Amount of quote asset to spend
            min_amount_out: Minimum amount of base asset to receive
            use_margin: Whether to use margin account
            fill_or_kill: Whether to revert if full quantity cannot be filled
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        function = self.contract.functions.placeAndExecuteMarketBuy(
            quote_size,
            min_amount_out,
            use_margin,
            fill_or_kill
        )
        return await self._build_and_send_transaction(function)

    async def place_market_sell(
        self,
        size: int,
        min_amount_out: int,
        use_margin: bool = False,
        fill_or_kill: bool = False
    ) -> str:
        """
        Place a market sell order
        
        Args:
            size: Amount of base asset to sell
            min_amount_out: Minimum amount of quote asset to receive
            use_margin: Whether to use margin account
            fill_or_kill: Whether to revert if full quantity cannot be filled
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        function = self.contract.functions.placeAndExecuteMarketSell(
            size,
            min_amount_out,
            use_margin,
            fill_or_kill
        )
        return await self._build_and_send_transaction(function)

    async def batch_cancel_orders(self, order_ids: List[int]) -> str:
        """
        Cancel multiple orders in batch
        
        Args:
            order_ids: List of order IDs to cancel
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        function = self.contract.functions.batchCancelOrders(order_ids)
        return await self._build_and_send_transaction(function)

    async def batch_update(
        self,
        buy_prices: List[int],
        buy_sizes: List[int],
        sell_prices: List[int],
        sell_sizes: List[int],
        cancel_order_ids: List[int],
        post_only: bool = False
    ) -> str:
        """
        Batch update orders - place multiple buy/sell orders and cancel orders in one transaction
        
        Args:
            buy_prices: List of buy order prices
            buy_sizes: List of buy order sizes
            sell_prices: List of sell order prices
            sell_sizes: List of sell order sizes
            cancel_order_ids: List of order IDs to cancel
            post_only: If True, orders will only be placed if they would be maker orders
            
        Returns:
            transaction_hash: Hash of the submitted transaction
        """
        function = self.contract.functions.batchUpdate(
            buy_prices,
            buy_sizes,
            sell_prices,
            sell_sizes,
            cancel_order_ids,
            post_only
        )
        return await self._build_and_send_transaction(function)

    async def get_best_bid_ask(self) -> Tuple[int, int]:
        """
        Get best bid and ask prices
        
        Returns:
            Tuple containing (best_bid, best_ask)
        """
        return await self.contract.functions.bestBidAsk().call()

    def _bytes_to_int(data: bytes, start: int, length: int = 32) -> int:
        """Convert bytes to integer"""
        return int.from_bytes(data[start:start + length], byteorder='big')

    def decode_l2_book(self, data: bytes, price_precision: float, size_precision: float) -> L2Book:
        """
        Decode the L2 book data from bytes
        
        Args:
            data: Raw bytes data from the contract
            price_precision: Price precision as float
            size_precision: Size precision as float
            
        Returns:
            L2Book object containing the decoded order book data
        """
        offset = 0
        
        # Get block number from first 32 bytes
        block_num = self._bytes_to_int(data, offset)
        offset += 32

        buy_orders = []
        sell_orders = []
        current_orders = buy_orders

        while offset + 32 <= len(data):
            price_bytes = data[offset:offset + 32]
            price = self._bytes_to_int(price_bytes)

            # Check for zero price (separator between buy and sell orders)
            if price == 0:
                current_orders = sell_orders
                offset += 32
                continue

            if offset + 64 > len(data):
                break

            size_bytes = data[offset + 32:offset + 64]
            size = self._bytes_to_int(size_bytes)

            # Convert to float and adjust for precision
            price_float = float(price) / price_precision
            size_float = float(size) / size_precision

            current_orders.append(OrderPriceSize(
                price=price_float,
                size=size_float
            ))

            offset += 64

        # Reverse sell orders to match Rust implementation
        sell_orders.reverse()

        return L2Book(
            block_num=block_num,
            buy_orders=buy_orders,
            sell_orders=sell_orders
        )

    async def amm_prices(self) -> Tuple[List[OrderPriceSize], List[OrderPriceSize]]:
        """
        Get AMM prices - implement this based on your AMM logic
        Returns tuple of (buy_orders, sell_orders)
        """
        # This is a placeholder - implement according to your AMM logic
        return [], []

    async def fetch_orderbook(self) -> L2Book:
        """
        Fetch and decode the complete L2 order book
        
        Returns:
            L2Book object containing the complete order book data
        """
        try:
            # Get raw L2 book data
            l2_book = await self.contract.functions.getL2Book().call()
            
            # Convert precision to float
            price_precision_float = float(self.market_params.price_precision)
            size_precision_float = float(self.market_params.size_precision)
            
            # Decode the book
            book = self.decode_l2_book(
                l2_book,
                price_precision_float,
                size_precision_float
            )
            
            # Get AMM prices
            amm_buy_orders, amm_sell_orders = await self.amm_prices()
            
            # Combine orderbook and AMM orders
            new_buy_orders = book.buy_orders + amm_buy_orders
            new_sell_orders = book.sell_orders + amm_sell_orders
            
            return L2Book(
                block_num=book.block_num,
                buy_orders=new_buy_orders,
                sell_orders=new_sell_orders
            )
            
        except Exception as e:
            raise Exception(f"Error fetching orderbook: {str(e)}")