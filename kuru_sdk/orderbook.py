from math import ceil, floor, log10
from web3 import Web3
from typing import Optional, List, Tuple, Dict, Any, NamedTuple
from dataclasses import dataclass
from decimal import Decimal
import json
from eth_utils import big_endian_to_int
import os

class OrderbookError:
    class NormalizationError(Exception):
        pass
    class EncodingError(Exception):
        pass
    class GasPriceError(Exception):
        pass
    class TransactionError(Exception):
        pass
    class GasEstimationError(Exception):
        def __init__(self, message: str):
            self.message = message
            super().__init__(self.message)

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

@dataclass
class TxOptions:
    gas_limit: Optional[int] = None
    gas_price: Optional[int] = None  # Used as maxFeePerGas
    max_priority_fee_per_gas: Optional[int] = None
    nonce: Optional[int] = None


@dataclass
class VaultParams:
    kuru_amm_vault: str
    vault_best_bid: int
    bid_partially_filled_size: int
    vault_best_ask: int
    ask_partially_filled_size: int
    vault_bid_order_size: int
    vault_ask_order_size: int

@dataclass
class OrderPriceSize:
    price: float
    size: float

@dataclass
class L2Book:
    block_num: int
    buy_orders: List[OrderPriceSize]
    sell_orders: List[OrderPriceSize]
    amm_buy_orders: List[OrderPriceSize]
    amm_sell_orders: List[OrderPriceSize]
    vault_params: VaultParams

    def __str__(self) -> str:
        # Combine regular and AMM orders
        combined_buys = {}
        combined_sells = {}

        # Process regular orders
        for order in self.buy_orders:
            combined_buys[order.price] = order.size
        for order in self.sell_orders:
            combined_sells[order.price] = order.size

        # Add AMM orders, combining sizes for matching prices
        for order in self.amm_buy_orders:
            combined_buys[order.price] = combined_buys.get(order.price, 0) + order.size
        for order in self.amm_sell_orders:
            combined_sells[order.price] = combined_sells.get(order.price, 0) + order.size

        # Convert to sorted lists
        sorted_buys = sorted(combined_buys.items(), key=lambda x: x[0], reverse=True)
        sorted_sells = sorted(combined_sells.items(), key=lambda x: x[0])

        # Format the table
        header = f"{'Price':>12} | {'Size':>12}"
        separator = "-" * 27
        rows = []

        # Add sell orders (highest to lowest)
        for price, size in sorted_sells:
            rows.append(f"{price:>12.8f} | {size:>12.8f}")

        # Add separator between sells and buys
        rows.append(separator)

        # Add buy orders (highest to lowest)
        for price, size in sorted_buys:
            rows.append(f"{price:>12.8f} | {size:>12.8f}")

        # Combine all parts
        return f"Block: {self.block_num}\n{header}\n{separator}\n" + "\n".join(rows)

@dataclass
class FormattedL2Book:
    block_num: int
    buy_orders: List[OrderPriceSize]
    sell_orders: List[OrderPriceSize]

    def __str__(self) -> str:
        # Format the table
        header = f"{'Price':>12} | {'Size':>12}"
        separator = "-" * 27
        rows = []

        # Add sell orders (highest to lowest)
        for order in sorted(self.sell_orders, key=lambda x: x.price):
            rows.append(f"{order.price:>12.8f} | {order.size:>12.8f}")

        # Add separator between sells and buys
        rows.append(separator)

        # Add buy orders (highest to lowest)
        for order in sorted(self.buy_orders, key=lambda x: x.price, reverse=True):
            rows.append(f"{order.price:>12.8f} | {order.size:>12.8f}")

        # Combine all parts
        return f"Block: {self.block_num}\n{header}\n{separator}\n" + "\n".join(rows)

class Orderbook:
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        private_key: str
    ):
        """
        Initialize the Orderbook SDK
        
        Args:
            web3: Web3 instance
            contract_address: Address of the deployed Orderbook contract
            private_key: Private key for signing transactions (optional)
        """
        self.web3 = web3
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.private_key = private_key
        
        # Load ABI from JSON file
        with open(os.path.join(os.path.dirname(__file__), 'abi/orderbook.json'), 'r') as f:
            contract_abi = json.load(f)
        
        self.contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=contract_abi
        )
        
        self.market_params = self._fetch_market_params()

    def _fetch_market_params(self) -> MarketParams:
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

    def normalize_with_precision(self, price: str, size: str) -> Tuple[int, int]:
        """Normalize price and size with contract precision"""
        try:
            price_normalized = float(price) * float(str(self.market_params.price_precision))
            size_normalized = float(size) * float(str(self.market_params.size_precision))
            return (int(price_normalized), int(size_normalized))
        except (ValueError, TypeError) as e:
            raise OrderbookError.NormalizationError(f"Error normalizing values: {str(e)}")

    async def _prepare_transaction(
        self, 
        function_name: str, 
        args: List[Any],
        tx_options: TxOptions,
        value: int = 0
    ) -> Dict:
        """Helper method to prepare transaction parameters"""
        func = getattr(self.contract.functions, function_name)(*args)

        tx = {
            'to': self.contract_address,
            'value': value,
            'data': func._encode_transaction_data(),
            'from': self.web3.eth.account.from_key(self.private_key).address,
            'type': '0x2',  # EIP-1559 transaction type
            'chainId': self.web3.eth.chain_id
        }

        # Get base fee from latest block
        base_fee = self.web3.eth.get_block('latest')['baseFeePerGas']

        # Set maxPriorityFeePerGas (tip) and maxFeePerGas
        if tx_options.gas_price is not None:
            tx['maxFeePerGas'] = tx_options.gas_price
            tx['maxPriorityFeePerGas'] = tx_options.max_priority_fee_per_gas or min(tx_options.gas_price - base_fee, tx_options.gas_price // 4)
        else:
            # Default to 2x current base fee for maxFeePerGas
            tx['maxFeePerGas'] = base_fee * 2
            # Default priority fee (can be adjusted based on network conditions)
            tx['maxPriorityFeePerGas'] = tx_options.max_priority_fee_per_gas or self.web3.eth.max_priority_fee

        # Ensure maxPriorityFeePerGas is not greater than maxFeePerGas
        if tx['maxPriorityFeePerGas'] > tx['maxFeePerGas']:
            tx['maxPriorityFeePerGas'] = tx['maxFeePerGas']
        
        if tx_options.gas_limit is None:
            estimated_gas = self.web3.eth.estimate_gas(tx)
            tx['gas'] = estimated_gas
        else:
            tx['gas'] = tx_options.gas_limit

        if tx_options.nonce is not None:
            tx['nonce'] = tx_options.nonce
        else:
            tx['nonce'] = self.web3.eth.get_transaction_count(tx['from'])
        return tx

    async def _execute_transaction(self, tx: Dict) -> Tuple[str, Optional[int]]:
        """Execute prepared transaction and return hash and order ID if applicable"""
        try:
            if self.private_key:
                signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
                tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            else:
                tx_hash = self.web3.eth.send_transaction(tx)
                
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return tx_hash.hex()
        except Exception as e:
            raise OrderbookError.TransactionError(f"Error executing transaction: {str(e)}")

    async def prepare_buy_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        tx_options: TxOptions = TxOptions()
    ) -> Dict:
        price_normalized, size_normalized = self.normalize_with_precision(price, size)
        return await self._prepare_transaction(
            "addBuyOrder",
            [price_normalized, size_normalized, post_only],
            tx_options
        )

    async def add_buy_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        tx_options: TxOptions = TxOptions()
    ) -> str:
        tx = await self.prepare_buy_order(price, size, post_only, tx_options)
        return await self._execute_transaction(tx)

    async def prepare_sell_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        tx_options: TxOptions = TxOptions()
    ) -> Dict:
        price_normalized, size_normalized = self.normalize_with_precision(price, size)
        return await self._prepare_transaction(
            "addSellOrder",
            [price_normalized, size_normalized, post_only],
            tx_options
        )

    async def add_sell_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        tx_options: TxOptions = TxOptions()
    ) -> str:
        tx = await self.prepare_sell_order(price, size, post_only, tx_options)
        return await self._execute_transaction(tx)

    async def prepare_batch_cancel_orders(
        self,
        order_ids: List[int],
        tx_options: TxOptions = TxOptions()
    ) -> Dict:
        return await self._prepare_transaction(
            "batchCancelOrders",
            [order_ids],
            tx_options
        )

    async def batch_cancel_orders(
        self,
        order_ids: List[int],
        tx_options: TxOptions = TxOptions()
    ) -> str:
        tx = await self.prepare_batch_cancel_orders(order_ids, tx_options)
        tx_hash = await self._execute_transaction(tx)
        return tx_hash
    
    async def prepare_market_buy(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        tx_options: TxOptions = TxOptions()
    ) -> Dict:
        size_normalized = float(size) * float(str(self.market_params.price_precision))
        min_amount_normalized = float(min_amount_out) * float(str(self.market_params.size_precision))
        
        return await self._prepare_transaction(
            "placeAndExecuteMarketBuy",
            [int(size_normalized), int(min_amount_normalized), is_margin, fill_or_kill],
            tx_options
        )

    async def market_buy(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        tx_options: TxOptions = TxOptions()
    ) -> str:
        tx = await self.prepare_market_buy(
            size, min_amount_out, is_margin, fill_or_kill, 
            tx_options
        )
        tx_hash = await self._execute_transaction(tx)
        return tx_hash

    async def prepare_market_sell(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        tx_options: TxOptions = TxOptions()
    ) -> Dict:
        size_normalized = float(size) * float(str(self.market_params.size_precision))
        min_amount_normalized = float(min_amount_out) * float(str(self.market_params.size_precision))
        return await self._prepare_transaction(
            "placeAndExecuteMarketSell",
            [int(size_normalized), int(min_amount_normalized), is_margin, fill_or_kill],
            tx_options
        )

    async def market_sell(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        tx_options: TxOptions = TxOptions()
    ) -> str:
        tx = await self.prepare_market_sell(
            size, min_amount_out, is_margin, fill_or_kill,
            tx_options
        )
        tx_hash = await self._execute_transaction(tx)
        return tx_hash

    async def prepare_batch_orders(
        self,
        buy_prices: List[str],
        buy_sizes: List[str],
        sell_prices: List[str],
        sell_sizes: List[str],
        order_ids_to_cancel: List[str],
        post_only: bool,
        tx_options: TxOptions = TxOptions()
    ) -> Dict:
        normalized_buy_prices = []
        normalized_buy_sizes = []
        normalized_sell_prices = []
        normalized_sell_sizes = []
        
        for price, size in zip(buy_prices, buy_sizes):
            price_norm, size_norm = self.normalize_with_precision(price, size)
            normalized_buy_prices.append(price_norm)
            normalized_buy_sizes.append(size_norm)
            
        for price, size in zip(sell_prices, sell_sizes):
            price_norm, size_norm = self.normalize_with_precision(price, size)
            normalized_sell_prices.append(price_norm)
            normalized_sell_sizes.append(size_norm)

        order_ids = [int(order_id) for order_id in order_ids_to_cancel]
        
        return await self._prepare_transaction(
            "batchUpdate",
            [
                normalized_buy_prices,
                normalized_buy_sizes,
                normalized_sell_prices,
                normalized_sell_sizes,
                order_ids,
                post_only
            ],
            tx_options
        )

    async def batch_orders(
        self,
        buy_prices: List[str],
        buy_sizes: List[str],
        sell_prices: List[str],
        sell_sizes: List[str],
        order_ids_to_cancel: List[str],
        post_only: bool,
        tx_options: TxOptions = TxOptions()
    ) -> str:
        tx = await self.prepare_batch_orders(
            buy_prices, buy_sizes, sell_prices, sell_sizes,
            order_ids_to_cancel, post_only, tx_options
        )
        tx_hash = await self._execute_transaction(tx)
        return tx_hash

    async def get_vault_params(self) -> Dict[str, Any]:
        """Fetch vault parameters from the contract"""
        try:
            # Call the contract function to get vault parameters
            vault_params = await self.contract.functions.getVaultParams().call()

            return {
                'kuru_amm_vault': vault_params[0],
                'vault_best_bid': int(vault_params[1]),
                'bid_partially_filled_size': int(vault_params[2]),
                'vault_best_ask': int(vault_params[3]),
                'ask_partially_filled_size': int(vault_params[4]),
                'vault_bid_order_size': int(vault_params[5]),
                'vault_ask_order_size': int(vault_params[6])
            }
        except Exception as e:
            print(f"Error fetching vault parameters: {str(e)}")
            raise OrderbookError(f"Failed to get vault params: {str(e)}")
        
    async def get_vault_params_from_contract(self) -> VaultParams:
        """Fetch vault parameters from the contract"""
        vault_params = self.contract.functions.getVaultParams().call()
        return VaultParams(
            kuru_amm_vault=vault_params[0],
            vault_best_bid=vault_params[1],
            bid_partially_filled_size=vault_params[2],
            vault_best_ask=vault_params[3],
            ask_partially_filled_size=vault_params[4],
            vault_bid_order_size=vault_params[5],
            vault_ask_order_size=vault_params[6]
        )
    
    async def fetch_orderbook(self) -> L2Book:
        """
        Fetch the current state of the orderbook including both regular orders and AMM prices.
        
        Returns:
            L2Book: Current state of the orderbook containing buy and sell orders
        """
        # Get raw L2 book data from contract
        l2_book_data = self.contract.functions.getL2Book().call()
        
        # Parse raw L2 data into price/size orders
        buy_orders = []
        sell_orders = []
        current_orders = buy_orders
        
        # First 32 bytes are block number
        block_num = int.from_bytes(l2_book_data[:32], 'big')
        offset = 32
        
        while offset + 32 <= len(l2_book_data):
            price_bytes = l2_book_data[offset:offset + 32]
            price = int.from_bytes(price_bytes, 'big')
            
            # Zero price indicates switch from buy to sell orders
            if price == 0:
                current_orders = sell_orders
                offset += 32
                continue
                
            if offset + 64 > len(l2_book_data):
                break
                
            size_bytes = l2_book_data[offset + 32:offset + 64]
            size = int.from_bytes(size_bytes, 'big')
            
            # Normalize price and size using market parameters
            price_float = float(price) / float(self.market_params.price_precision)
            size_float = float(size) / float(self.market_params.size_precision)
            
            current_orders.append(OrderPriceSize(
                price=price_float,
                size=size_float
            ))
            
            offset += 64
        
        # Reverse sell orders to show highest price first
        sell_orders.reverse()
        
        # Get AMM prices
        amm_prices = await self._get_amm_prices()
        total_decimals = log10(self.market_params.price_precision / self.market_params.tick_size)
        
        [amm_buy_orders, amm_sell_orders] = amm_prices


        # round buy_orders down to total_decimals
        # round sell_orders up to total_decimals
        buy_orders = [OrderPriceSize(price=floor(order.price * 10**total_decimals) / 10**total_decimals, size=order.size) for order in buy_orders]
        sell_orders = [OrderPriceSize(price=ceil(order.price * 10**total_decimals) / 10**total_decimals, size=order.size) for order in sell_orders]
        
        vault_params = await self.get_vault_params_from_contract()

        return L2Book(
            block_num=block_num,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            amm_buy_orders=amm_buy_orders, 
            amm_sell_orders=amm_sell_orders,
            vault_params=vault_params
        )

    async def _get_amm_prices(self) -> Tuple[List[OrderPriceSize], List[OrderPriceSize]]:
        """
        Get the AMM vault prices for both buy and sell sides.
        
        Returns:
            Tuple[List[OrderPriceSize], List[OrderPriceSize]]: Buy and sell orders from AMM
        """
        TOTAL_PRICE_POINTS = 300
        bids = []
        asks = []
        
        # Get vault parameters
        vault_params = self.contract.functions.getVaultParams().call()
        
        vault_best_bid = vault_params[1]
        vault_best_ask = vault_params[3]
        vault_bid_order_size = vault_params[5]
        vault_ask_order_size = vault_params[6]
        kuru_amm_vault = vault_params[0]
        bid_partially_filled_size = vault_params[2]
        ask_partially_filled_size = vault_params[4]
        
        # Convert sizes to float using precision
        vault_bid_size_float = float(vault_bid_order_size) / float(self.market_params.size_precision)
        vault_ask_size_float = float(vault_ask_order_size) / float(self.market_params.size_precision)
        
        # Calculate first order sizes accounting for partial fills
        first_bid_size = float(vault_bid_order_size - bid_partially_filled_size) / float(self.market_params.size_precision)
        first_ask_size = float(vault_ask_order_size - ask_partially_filled_size) / float(self.market_params.size_precision)
        
        # Skip if no AMM vault or no bid size
        if vault_bid_order_size == 0 or kuru_amm_vault == "0x0000000000000000000000000000000000000000":
            return bids, asks
            
        # Generate bid prices
        for i in range(TOTAL_PRICE_POINTS):
            if vault_best_bid == 0:
                break
                
            bids.append(OrderPriceSize(
                price=self._wei_to_eth(vault_best_bid),
                size=first_bid_size if i == 0 else vault_bid_size_float
            ))
            
            # Update price and size for next level
            vault_best_bid = (vault_best_bid * 1000) // 1003
            vault_bid_order_size = (vault_bid_order_size * 2003) // 2000
            vault_bid_size_float = float(vault_bid_order_size) / float(self.market_params.size_precision)
        
        # Generate ask prices
        for i in range(TOTAL_PRICE_POINTS):
            if vault_best_ask >= (2**256 - 1):  # Check for uint256 overflow
                break
                
            asks.append(OrderPriceSize(
                price=self._wei_to_eth(vault_best_ask),
                size=first_ask_size if i == 0 else vault_ask_size_float
            ))
            
            # Update price and size for next level
            vault_best_ask = (vault_best_ask * 1003) // 1000
            vault_ask_order_size = (vault_ask_order_size * 2000) // 2003
            vault_ask_size_float = float(vault_ask_order_size) / float(self.market_params.size_precision)
        
        return bids, asks
    
    def _get_amm_prices_for_vault(self, vault_params: VaultParams) -> Tuple[List[OrderPriceSize], List[OrderPriceSize]]:
        """
        Get the AMM vault prices for both buy and sell sides.
        
        Returns:
            Tuple[List[OrderPriceSize], List[OrderPriceSize]]: Buy and sell orders from AMM
        """
        TOTAL_PRICE_POINTS = 300
        bids = []
        asks = []
        
        
        vault_best_bid = vault_params.vault_best_bid
        vault_best_ask = vault_params.vault_best_ask
        vault_bid_order_size = vault_params.vault_bid_order_size
        vault_ask_order_size = vault_params.vault_ask_order_size
        kuru_amm_vault = vault_params.kuru_amm_vault
        bid_partially_filled_size = vault_params.bid_partially_filled_size
        ask_partially_filled_size = vault_params.ask_partially_filled_size
        
        # Convert sizes to float using precision
        vault_bid_size_float = float(vault_bid_order_size) / float(self.market_params.size_precision)
        vault_ask_size_float = float(vault_ask_order_size) / float(self.market_params.size_precision)
        
        # Calculate first order sizes accounting for partial fills
        first_bid_size = float(vault_bid_order_size - bid_partially_filled_size) / float(self.market_params.size_precision)
        first_ask_size = float(vault_ask_order_size - ask_partially_filled_size) / float(self.market_params.size_precision)
        
        # Skip if no AMM vault or no bid size
        if vault_bid_order_size == 0 or kuru_amm_vault == "0x0000000000000000000000000000000000000000":
            return bids, asks
            
        # Generate bid prices
        for i in range(TOTAL_PRICE_POINTS):
            if vault_best_bid == 0:
                break
                
            bids.append(OrderPriceSize(
                price=self._wei_to_eth(vault_best_bid),
                size=first_bid_size if i == 0 else vault_bid_size_float
            ))
            
            # Update price and size for next level
            vault_best_bid = (vault_best_bid * 1000) // 1003
            vault_bid_order_size = (vault_bid_order_size * 2003) // 2000
            vault_bid_size_float = float(vault_bid_order_size) / float(self.market_params.size_precision)
        
        # Generate ask prices
        for i in range(TOTAL_PRICE_POINTS):
            if vault_best_ask >= (2**256 - 1):  # Check for uint256 overflow
                break
                
            asks.append(OrderPriceSize(
                price=self._wei_to_eth(vault_best_ask),
                size=first_ask_size if i == 0 else vault_ask_size_float
            ))
            
            # Update price and size for next level
            vault_best_ask = (vault_best_ask * 1003) // 1000
            vault_ask_order_size = (vault_ask_order_size * 2000) // 2003
            vault_ask_size_float = float(vault_ask_order_size) / float(self.market_params.size_precision)
        
        return bids, asks

    def _wei_to_eth(self, wei_value: int) -> float:
        """Convert Wei to ETH"""
        return float(wei_value) / 1e18
    
    def reconcile_orderbook(self, orderbook: L2Book, event: str, payload: Dict) -> L2Book:
        """Reconcile the orderbook to ensure it is updated with new orders / trades"""

        if event == "OrderCreated":
            orderbook = self._reconcile_orderbook_for_order_created(orderbook, payload)
            
        elif event == "OrderCancelled":
            orderbook = self._reconcile_orderbook_for_order_cancelled(orderbook, payload)
        elif event == "Trade":
            orderbook = self._reconcile_orderbook_for_trade(orderbook, payload)

        return orderbook
    


    def _reconcile_orderbook_for_order_created(self, orderbook: L2Book, payload: Dict) -> L2Book:
        """Reconcile the orderbook for an order created event"""
        total_decimals = log10(self.market_params.price_precision / self.market_params.tick_size)
        is_buy = payload['isBuy']
        size = payload['size'] / self.market_params.size_precision

        buy_orders = orderbook.buy_orders
        sell_orders = orderbook.sell_orders
        block_num = payload['blockNumber']

        if is_buy:
            price = floor((payload['price'] / 10**18) * 10**total_decimals) / 10**total_decimals 
            # find the corresponding price in the buy_orders list
            for order in buy_orders:
                if order.price == price:
                    order.size += size
                    break
            else:
                buy_orders.append(OrderPriceSize(price=price, size=size))
        else:
            price = ceil((payload['price'] / 10**18) * 10**total_decimals) / 10**total_decimals 
            # find the corresponding price in the sell_orders list
            for order in sell_orders:
                if order.price == price:
                    order.size += size
                    break
            else:
                sell_orders.append(OrderPriceSize(price=price, size=size))

        return L2Book(
            block_num=block_num,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            amm_buy_orders=orderbook.amm_buy_orders,
            amm_sell_orders=orderbook.amm_sell_orders,
            vault_params=orderbook.vault_params
        )
    
    def _reconcile_orderbook_for_order_cancelled(self, orderbook: L2Book, payload: Dict) -> L2Book:
        """Reconcile the orderbook for an order cancelled event"""
        
        total_decimals = log10(self.market_params.price_precision / self.market_params.tick_size)

        orders_cancelled = payload['canceledOrdersData']

        block_num = orders_cancelled[0]['blockNumber']
        buy_orders = orderbook.buy_orders
        sell_orders = orderbook.sell_orders

        for order in orders_cancelled:
            if order['isBuy']:
                size = order['size'] / self.market_params.size_precision
                price = floor((payload['price'] / 10**18) * 10**total_decimals) / 10**total_decimals
                # find the corresponding price in the buy_orders list
                for order in buy_orders:
                    if order.price == price:
                        order.size -= size
                        break
                else:
                    buy_orders.append(OrderPriceSize(price=price, size=size))
            else:
                size = order['size'] / self.market_params.size_precision
                price = ceil((payload['price'] / 10**18) * 10**total_decimals) / 10**total_decimals
                # find the corresponding price in the sell_orders list
                for order in sell_orders:
                    if order.price == price:
                        order.size -= size
                        break

        return L2Book(
            block_num=block_num,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            amm_buy_orders=orderbook.amm_buy_orders,
            amm_sell_orders=orderbook.amm_sell_orders,
            vault_params=orderbook.vault_params
        )
    
    def _reconcile_orderbook_for_trade(self, orderbook: L2Book, payload: Dict) -> L2Book:
        block_num = payload['blockNumber']
        new_orderbook = L2Book(
            block_num=block_num,
            buy_orders=orderbook.buy_orders,
            sell_orders=orderbook.sell_orders,
            vault_params=orderbook.vault_params
        )

        total_decimals = log10(self.market_params.price_precision / self.market_params.tick_size)

        order_id = payload['orderId']

        if order_id == 0:
            # amm trade
            new_orderbook = self._handle_amm_trade(new_orderbook, payload)
        else:
            # regular trade
            new_orderbook = self._handle_regular_trade(new_orderbook, payload)


    def _handle_amm_trade(self, orderbook: L2Book, payload: Dict) -> L2Book:
        """Handle an AMM trade event"""
        is_buy = payload['isBuy']

        SPREAD = orderbook.vault_params.spread / 10
        updated_size = payload['size']

        if is_buy:

            if updated_size == 0:
                orderbook.vault_params.vault_best_ask = (orderbook.vault_params.vault_best_ask * (1000 + SPREAD)) // 1000
                orderbook.vault_params.vault_best_bid = (orderbook.vault_params.vault_best_bid * 1000) // (1000 + SPREAD)
                orderbook.vault_params.vault_ask_order_size = (orderbook.vault_params.vault_ask_order_size * 2000) // (2000 + SPREAD)
                orderbook.vault_params.vault_bid_order_size = (orderbook.vault_params.vault_ask_order_size * (2000 + SPREAD)) // 2000
                orderbook.vault_params.ask_partially_filled_size = 0
                orderbook.vault_params.bid_partially_filled_size = (orderbook.vault_params.bid_partially_filled_size * 1000) // (1000 + SPREAD)

            else:
                orderbook.vault_params.ask_partially_filled_size = orderbook.vault_params.vault_ask_order_size - updated_size
            
        else:
            if updated_size == 0:
                orderbook.vault_params.vault_best_bid = (orderbook.vault_params.vault_best_bid * 1000) // (1000 + SPREAD)
                orderbook.vault_params.vault_best_ask = (orderbook.vault_params.vault_best_ask * (1000 + SPREAD)) // 1000
                orderbook.vault_params.vault_bid_order_size = (orderbook.vault_params.vault_bid_order_size * (2000 + SPREAD)) // 2000
                orderbook.vault_params.vault_ask_order_size = (orderbook.vault_params.vault_bid_order_size * 2000) // (2000 + SPREAD)
                orderbook.vault_params.bid_partially_filled_size = 0
                
            else:
                orderbook.vault_params.bid_partially_filled_size = orderbook.vault_params.vault_bid_order_size - updated_size
            

        amm_prices = self._get_amm_prices_for_vault(orderbook.vault_params)
        
        orderbook.amm_buy_orders = amm_prices[0]
        orderbook.amm_sell_orders = amm_prices[1]

        return orderbook


    def _handle_regular_trade(self, orderbook: L2Book, payload: Dict) -> L2Book:
        """Handle a regular trade event"""
        filled_size = payload['filledSize'] / self.market_params.size_precision  # Fixed conversion

        raw_trade_price = payload['price']  # Price should already be in correct format from contract
        formatted_price = self.format_price(raw_trade_price, payload['isBuy'])

        side_to_update = orderbook.buy_orders if payload['isBuy'] else orderbook.sell_orders

        # Find the order at the given price level
        for i, order in enumerate(side_to_update):
            if order.price == formatted_price:
                # Update the size
                new_size = order.size - filled_size
                if new_size <= 0:
                    # Remove the price level if size is zero or negative
                    side_to_update.pop(i)
                else:
                    # Update the size if there's remaining quantity
                    side_to_update[i] = OrderPriceSize(price=formatted_price, size=new_size)
                break

        # Update the appropriate side in the orderbook
        if payload['isBuy']:
            orderbook.buy_orders = side_to_update
        else:
            orderbook.sell_orders = side_to_update

        return orderbook

    def format_price(self, price: int, is_buy: bool) -> float:
        """Format a price to the correct precision"""
        total_decimals = log10(self.market_params.price_precision / self.market_params.tick_size)
        if is_buy:
            return floor(price / 10**18 * 10**total_decimals) / 10**total_decimals
        else:
            return ceil(price / 10**18 * 10**total_decimals) / 10**total_decimals

    def get_formatted_orderbook(self) -> FormattedL2Book:
        """
        Combines regular and AMM orders into a single formatted orderbook.
        
        Returns:
            FormattedL2Book: Combined orderbook with merged regular and AMM orders
        """
        # Combine regular and AMM orders
        combined_buys = {}
        combined_sells = {}

        # Process regular orders
        for order in self.buy_orders:
            combined_buys[order.price] = order.size
        for order in self.sell_orders:
            combined_sells[order.price] = order.size

        # Add AMM orders, combining sizes for matching prices
        for order in self.amm_buy_orders:
            combined_buys[order.price] = combined_buys.get(order.price, 0) + order.size
        for order in self.amm_sell_orders:
            combined_sells[order.price] = combined_sells.get(order.price, 0) + order.size

        # Convert back to OrderPriceSize objects
        formatted_buys = [
            OrderPriceSize(price=price, size=size)
            for price, size in combined_buys.items()
        ]
        formatted_sells = [
            OrderPriceSize(price=price, size=size)
            for price, size in combined_sells.items()
        ]

        return FormattedL2Book(
            block_num=self.block_num,
            buy_orders=formatted_buys,
            sell_orders=formatted_sells
        )

__all__ = ['Orderbook']
