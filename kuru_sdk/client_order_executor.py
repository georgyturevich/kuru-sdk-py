from web3 import Web3
from web3 import AsyncWeb3
from typing import Dict, List, Optional, Union
import asyncio

from kuru_sdk.orderbook import Orderbook, TxOptions
from kuru_sdk.types import L2Book, Order, OrderCreatedEvent, OrderPriceSize, OrderRequest
from kuru_sdk.api import KuruAPI

class ClientOrderExecutor:
    def __init__(self,
                 web3: Union[Web3, AsyncWeb3],
                 contract_address: str,
                 private_key: Optional[str] = None,
                 kuru_api_url: Optional[str] = None,
             ):
        
        # Use orderbook with async-compatible web3
        self.orderbook = Orderbook(web3, contract_address, private_key)
        self.kuru_api = KuruAPI(kuru_api_url)
        
        # Always use AsyncWeb3
        from web3 import AsyncHTTPProvider
        if isinstance(web3, AsyncWeb3):
            # Already async, just use it
            self.web3 = web3
        elif hasattr(web3.provider, 'endpoint_uri'):
            # Convert to AsyncWeb3
            endpoint = web3.provider.endpoint_uri
            self.web3 = AsyncWeb3(AsyncHTTPProvider(endpoint))
        else:
            raise ValueError("Cannot determine provider endpoint for Web3 instance")
            
        # Store account info
        if private_key:
            self.account = web3.eth.account.from_key(private_key)
            self.wallet_address = self.account.address
        
        # storage dicts
        self.cloid_to_order_id: Dict[str, int] = {}
        self.order_id_to_cloid: Dict[int, str] = {}
        self.cloid_to_order: Dict[str, OrderRequest] = {}

    # async def connect(self):
    #     if self.websocket_handler:
    #         # Start the websocket connection in the background
    #         asyncio.create_task(self.websocket_handler.connect())
    #         await asyncio.sleep(2)
    #     else:
    #         print("No websocket handler provided")

    # async def disconnect(self):
    #     if self.websocket_handler:
    #         await self.websocket_handler.disconnect()
    #     else:
    #         print("No websocket handler provided")

    async def place_order(self, order: OrderRequest, tx_options: Optional[TxOptions] = TxOptions()) -> str:
        """
        Place an order with the given parameters
        Returns the transaction hash
        """
        
        cloid = order.cloid

        try:
            tx_hash = None
            if order.order_type == "limit":

                if not order.price:
                    raise ValueError("Price is required for limit orders")
                if not order.size:
                    raise ValueError("Size is required for limit orders")
                
                if order.side == "buy":
                    print(f"Adding buy order with price: {order.price}, size: {order.size}, post_only: {order.post_only}, tx_options: {tx_options}")
                    tx_hash = await self.orderbook.add_buy_order(
                        price=order.price,
                        size=order.size,
                        post_only=order.post_only,
                        tick_normalization=order.tick_normalization,
                        tx_options=tx_options
                    )
                else:  # sell
                    tx_hash = await self.orderbook.add_sell_order(
                        price=order.price,
                        size=order.size,
                        post_only=order.post_only,
                        tick_normalization=order.tick_normalization,
                        tx_options=tx_options
                    )
            else:  # market
                if not order.min_amount_out:
                    raise ValueError("min_amount_out is required for market orders")
                if not order.size:
                    raise ValueError("Size is required for market orders")
                
                if order.side == "buy":
                    tx_hash = await self.orderbook.market_buy(
                        size=order.size,
                        min_amount_out=order.min_amount_out,
                        is_margin=order.is_margin,
                        fill_or_kill=order.fill_or_kill,
                        tx_options=tx_options
                    )
                else:  # sell
                    tx_hash = await self.orderbook.market_sell(
                        size=order.size,
                        min_amount_out=order.min_amount_out,
                        is_margin=order.is_margin,
                        fill_or_kill=order.fill_or_kill,
                        tx_options=tx_options
                    )

            if order.order_type == "cancel":
                tx_hash = await self.cancel_orders(cloids=[cloid], tx_options=tx_options)

            # Wait for the transaction receipt asynchronously
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                if cloid:
                    order_id = self.orderbook.get_order_id_from_receipt(receipt)
                    print(f"Order ID: {order_id}")
                    if order_id:
                        self.cloid_to_order_id[cloid] = order_id
                        self.order_id_to_cloid[order_id] = cloid
                    print(f"Transaction successful for cloid {cloid}, tx_hash: {receipt.transactionHash.hex()}")
                return receipt.transactionHash.hex() # Return the full receipt object
            else:
                raise Exception(f"Order failed: Transaction status {receipt.status}, receipt: {receipt}")

        except Exception as e:
            print(f"Error placing order: {e}")
            raise
        
    async def cancel_orders(self, cloids: Optional[List[str]] = None, order_ids: Optional[List[int]] = None, tx_options: Optional[TxOptions] = TxOptions()) -> str:
        """
        Cancel orders with the given cloids or order_ids
        """
        if not (cloids or order_ids):
            raise ValueError("Either cloids or order_ids must be provided for cancel orders")
            
        if cloids:
            order_ids = []
            for cloid in cloids:
                if cloid in self.cloid_to_order_id:
                    order_ids.append(self.cloid_to_order_id[cloid])
                else:
                    raise ValueError(f"Order ID not found for cloid: {cloid}")

        tx_hash = await self.orderbook.batch_orders(order_ids_to_cancel=order_ids, tx_options=tx_options)
        
        # Wait for the transaction receipt asynchronously
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
        return receipt.transactionHash.hex()
    
    async def batch_orders(
        self,
        orders: List[OrderRequest],
        tx_options: Optional[TxOptions] = TxOptions()
    ) -> List[str]:
        """
        Place multiple orders in a single transaction
        """

        buy_prices = []
        buy_sizes = []
        sell_prices = []
        sell_sizes = []
        order_ids_to_cancel = []
        post_only = False

        for order in orders:
            if order.order_type == "cancel":
                if not (order.cancel_order_ids or order.cancel_cloids):
                    raise ValueError("Either cancel_order_ids or cancel_cloids must be provided for cancel orders")
                if order.cancel_order_ids:
                    order_ids_to_cancel.extend(order.cancel_order_ids)
                elif order.cancel_cloids:
                    for cloid in order.cancel_cloids:
                        if cloid in self.cloid_to_order_id:
                            order_ids_to_cancel.append(self.cloid_to_order_id[cloid])
                        else:
                            raise ValueError(f"Order ID not found for cloid: {cloid}")
                continue
            
            if order.side == "buy":
                buy_prices.append(order.price)
                buy_sizes.append(order.size)
            elif order.side == "sell":
                sell_prices.append(order.price)
                sell_sizes.append(order.size)

            post_only = post_only or (order.post_only if order.post_only is not None else False)

        tx_hash = await self.orderbook.batch_orders(
            buy_prices=buy_prices,
            buy_sizes=buy_sizes,
            sell_prices=sell_prices,
            sell_sizes=sell_sizes,
            order_ids_to_cancel=order_ids_to_cancel,
            post_only=post_only,
            tx_options=tx_options
        )

        # Wait for the transaction receipt asynchronously
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status == 1:
            order_created_events = self.orderbook.decode_logs(receipt)
            self.match_orders_with_events(orders, order_created_events)
            print(f"Transaction successful for batch orders, tx_hash: {receipt.transactionHash.hex()}")
            print(f"Order IDs: {self.cloid_to_order_id}")
            return receipt.transactionHash.hex()
        else:
            raise Exception(f"Batch order failed: Transaction status {receipt.status}, receipt: {receipt}")
        

    # async def cancel_all_active_orders_for_market(self, tx_options: Optional[TxOptions] = TxOptions()):


    def get_order_id_by_cloid(self, cloid: str) -> int:
        return self.cloid_to_order_id[cloid]

    def match_orders_with_events(self, orders: List[OrderRequest], events: List[OrderCreatedEvent]) -> List[OrderRequest]:
        """
        Match orders with events based the price and isBuy field
        """

        for order in orders:
            if order.order_type == "cancel" or order.order_type == "market":
                continue
            for event in events:
                if order.price * self.orderbook.market_params.price_precision == event.price and order.side == ("buy" if event.is_buy else "sell"):
                    self.cloid_to_order_id[order.cloid] = event.order_id
                    self.order_id_to_cloid[event.order_id] = order.cloid
    
    
    async def get_l2_book(self):
        return await self.orderbook.get_l2_book()
    
    def get_order_by_cloid(self, cloid: str) -> OrderRequest:
        return self.cloid_to_order[cloid]
    
    def get_order_id_by_cloid(self, cloid: str) -> int:
        return self.cloid_to_order_id[cloid]


    ## Kuru API
    async def get_order_history(self, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Order]:
        return await self.kuru_api.get_order_history(self.wallet_address)
    
    async def get_trades(self, market_address: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Order]:
        return await self.kuru_api.get_trades(market_address, self.wallet_address, start_timestamp, end_timestamp)
    
    async def get_orders_by_ids(self, market_address: str, order_ids: List[int]) -> List[Order]:
        return await self.kuru_api.get_orders_by_ids(market_address, order_ids)

    async def get_orders_by_cloids(self, market_address: str, cloids: List[str]) -> List[Order]:
        order_ids = [self.cloid_to_order_id[cloid] for cloid in cloids]
        return await self.get_orders_by_ids(market_address, order_ids)
    
    async def get_user_orders(self) -> List[Order]:
        return await self.kuru_api.get_user_orders(self.wallet_address)
        
    async def close(self):
        """Close the API client session"""
        await self.kuru_api.close()
    
    