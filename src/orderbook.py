from web3 import Web3
from typing import Optional, List, Tuple, Dict, Any, NamedTuple
from dataclasses import dataclass
from decimal import Decimal
import json

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

class Orderbook:
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        private_key: Optional[str] = None
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
        with open('abi/orderbook.json', 'r') as f:
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
            'from': self.web3.eth.default_account if not self.private_key else
                   self.web3.eth.account.from_key(self.private_key).address,
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
    ) -> Tuple[str, int]:
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
    ) -> Tuple[str, int]:
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
        print(f"Market sell transaction hash: {tx_hash}")
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
      
__all__ = ['Orderbook']