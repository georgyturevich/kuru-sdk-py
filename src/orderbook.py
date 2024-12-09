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
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None,
        value: int = 0
    ) -> Dict:
        """Helper method to prepare transaction parameters"""
        func = self.contract.get_function_by_name(function_name)
        data = func.encode_input(*args)
        
        tx = {
            'to': self.contract_address,
            'value': value,
            'data': data,
            'from': self.web3.eth.default_account if not self.private_key else
                   self.web3.eth.account.from_key(self.private_key).address
        }

        tx['gasPrice'] = gas_price if gas_price is not None else \
                        await self.web3.eth.gas_price

        if gas_limit is None:
            estimated_gas = await self.web3.eth.estimate_gas(tx)
            tx['gas'] = estimated_gas * 3 // 2
        else:
            tx['gas'] = gas_limit

        if nonce is not None:
            tx['nonce'] = nonce

        return tx

    async def _execute_transaction(self, tx: Dict) -> Tuple[str, Optional[int]]:
        """Execute prepared transaction and return hash and order ID if applicable"""
        try:
            if self.private_key:
                signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            else:
                tx_hash = await self.web3.eth.send_transaction(tx)
                
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
            order_id = self._get_order_id_from_receipt(receipt)
            
            return (tx_hash.hex(), order_id)
        except Exception as e:
            raise OrderbookError.TransactionError(f"Error executing transaction: {str(e)}")

    async def prepare_buy_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict:
        price_normalized, size_normalized = self.normalize_with_precision(price, size)
        return await self._prepare_transaction(
            "addBuyOrder",
            [price_normalized, size_normalized, post_only],
            nonce,
            gas_price,
            gas_limit
        )

    async def add_buy_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Tuple[str, int]:
        tx = await self.prepare_buy_order(price, size, post_only, nonce, gas_price, gas_limit)
        return await self._execute_transaction(tx)

    async def prepare_sell_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict:
        price_normalized, size_normalized = self.normalize_with_precision(price, size)
        return await self._prepare_transaction(
            "addSellOrder",
            [price_normalized, size_normalized, post_only],
            nonce,
            gas_price,
            gas_limit
        )

    async def add_sell_order(
        self,
        price: str,
        size: str,
        post_only: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Tuple[str, int]:
        tx = await self.prepare_sell_order(price, size, post_only, nonce, gas_price, gas_limit)
        return await self._execute_transaction(tx)

    async def prepare_batch_cancel_orders(
        self,
        order_ids: List[int],
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict:
        return await self._prepare_transaction(
            "batchCancelOrders",
            [order_ids],
            nonce,
            gas_price,
            gas_limit
        )

    async def batch_cancel_orders(
        self,
        order_ids: List[int],
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        tx = await self.prepare_batch_cancel_orders(order_ids, nonce, gas_price, gas_limit)
        tx_hash, _ = await self._execute_transaction(tx)
        return tx_hash

    async def prepare_market_buy(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict:
        size_normalized = float(size) * float(str(self.market_params.price_precision))
        min_amount_normalized = float(min_amount_out) * float(str(self.market_params.size_precision))
        
        return await self._prepare_transaction(
            "placeAndExecuteMarketBuy",
            [int(size_normalized), int(min_amount_normalized), is_margin, fill_or_kill],
            nonce,
            gas_price,
            gas_limit
        )

    async def market_buy(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        tx = await self.prepare_market_buy(
            size, min_amount_out, is_margin, fill_or_kill, 
            nonce, gas_price, gas_limit
        )
        tx_hash, _ = await self._execute_transaction(tx)
        return tx_hash

    async def prepare_market_sell(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict:
        size_normalized = float(size) * float(str(self.market_params.size_precision))
        min_amount_normalized = float(min_amount_out) * float(str(self.market_params.size_precision))
        
        return await self._prepare_transaction(
            "placeAndExecuteMarketSell",
            [int(size_normalized), int(min_amount_normalized), is_margin, fill_or_kill],
            nonce,
            gas_price,
            gas_limit
        )

    async def market_sell(
        self,
        size: str,
        min_amount_out: str,
        is_margin: bool,
        fill_or_kill: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        tx = await self.prepare_market_sell(
            size, min_amount_out, is_margin, fill_or_kill,
            nonce, gas_price, gas_limit
        )
        tx_hash, _ = await self._execute_transaction(tx)
        return tx_hash

    async def prepare_batch_orders(
        self,
        buy_prices: List[str],
        buy_sizes: List[str],
        sell_prices: List[str],
        sell_sizes: List[str],
        order_ids_to_cancel: List[str],
        post_only: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
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
            nonce,
            gas_price,
            gas_limit
        )

    async def batch_orders(
        self,
        buy_prices: List[str],
        buy_sizes: List[str],
        sell_prices: List[str],
        sell_sizes: List[str],
        order_ids_to_cancel: List[str],
        post_only: bool,
        nonce: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        tx = await self.prepare_batch_orders(
            buy_prices, buy_sizes, sell_prices, sell_sizes,
            order_ids_to_cancel, post_only, nonce, gas_price, gas_limit
        )
        tx_hash, _ = await self._execute_transaction(tx)
        return tx_hash

    def _get_order_id_from_receipt(self, receipt: Dict) -> Optional[int]:
      """
      Extract order ID from transaction receipt logs
      
      Args:
          receipt: Transaction receipt containing logs
          
      Returns:
          Order ID as integer or None if not found
        """
      try:
          if not receipt.get('logs') or len(receipt['logs']) == 0:
              return None
              
          # Get the first log
          log = receipt['logs'][0]
          
          # Get the log data without '0x' prefix
          data = log['data'][2:]
          
          # Split data into 32-byte chunks
          chunks = [data[i:i+64] for i in range(0, len(data), 64)]
          
          if not chunks:
              return None
              
          # Convert first chunk to integer
          order_id = int(chunks[0], 16)
          
          return order_id
      except Exception as e:
          print(f"Error extracting order ID: {str(e)}")
          return None
      


__all__ = ['Orderbook']