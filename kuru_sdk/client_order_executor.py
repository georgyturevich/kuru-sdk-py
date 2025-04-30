from web3 import Web3

from kuru_sdk.orderbook import Orderbook, TxOptions
from typing import Dict, List, Optional, Callable, Awaitable, Any, Union
from kuru_sdk.types import L2Book, Order, OrderCreatedEvent, OrderPriceSize, OrderRequest, OrderResponse, TradeResponse
from kuru_sdk.api import KuruAPI
import asyncio
import logging
from collections import deque

class ClientOrderExecutor:
    def __init__(self,
                 web3: Web3,
                 contract_address: str,
                 private_key: Optional[str] = None,
                 kuru_api_url: Optional[str] = None,
                 logger: Union[logging.Logger, bool] = True,
             ):
        
        self.web3 = web3
        self.orderbook = Orderbook(web3, contract_address, private_key, logger=logger)
        self.kuru_api = KuruAPI(kuru_api_url)
        self.wallet_address = self.web3.eth.account.from_key(private_key).address
        
        # Set up logger
        if isinstance(logger, logging.Logger):
            self.logger = logger
        elif logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = None
        
        self.market_address = contract_address
        # storage dicts
        self.cloid_to_order_id: Dict[str, int] = {}
        self.order_id_to_cloid: Dict[int, str] = {}
        self.cloid_to_order: Dict[str, OrderRequest] = {}

        # Transaction processing queue and background task
        self.tx_queue = deque()
        self.tx_callbacks = {}  # Map tx_hash -> callback function
        self.tx_processor_task = None
        self.is_processing = False

    async def start_tx_processor(self):
        """Start the background transaction processor if not already running"""
        if not self.is_processing:
            self.is_processing = True
            self.tx_processor_task = asyncio.create_task(self._process_tx_queue())
    
    async def stop_tx_processor(self):
        """Stop the background transaction processor"""
        if self.is_processing and self.tx_processor_task:
            self.is_processing = False
            await self.tx_processor_task
            self.tx_processor_task = None
    
    async def _process_tx_queue(self):
        """Background task to process transaction receipts"""
        while self.is_processing:
            if self.tx_queue:
                tx_hash, orders = self.tx_queue.popleft()
                try:
                    receipt = await asyncio.to_thread(
                        self.web3.eth.wait_for_transaction_receipt, 
                        tx_hash
                    )
                    
                    if receipt.status == 1:
                        order_created_events = self.orderbook.decode_logs(receipt)
                        self.match_orders_with_events(orders, order_created_events)
                        self._log_info(f"Transaction successful for batch orders, tx_hash: {receipt.transactionHash.hex()}")
                        self._log_info(f"Order IDs: {self.cloid_to_order_id}")
                    else:
                        self._log_error(f"Batch order failed: Transaction status {receipt.status}, tx_hash: {receipt.transactionHash.hex()}")
                    
                    # Execute callback if one exists
                    if tx_hash in self.tx_callbacks:
                        callback, callback_args = self.tx_callbacks.pop(tx_hash)
                        if callback:
                            await callback(receipt, *callback_args)
                        
                except Exception as e:
                    self._log_error(f"Error processing transaction {tx_hash}: {e}")
            else:
                # Wait a bit before checking queue again
                await asyncio.sleep(0.1)

    async def place_order(
        self, 
        order: OrderRequest, 
        tx_options: Optional[TxOptions] = TxOptions(),
        callback: Optional[Callable[[Any, OrderRequest], Awaitable[None]]] = None,
        callback_args: tuple = (),
        async_execution: bool = False
    ) -> str:
        """
        Place an order with the given parameters
        Returns the cloid (client order ID) for the order
        """
        
        # Generate cloid if not provided
        if not order.cloid:
            # We'll temporarily set a placeholder and update it after getting tx_hash
            order.cloid = "pending_cloid_"
        
        cloid = order.cloid
        market_address = order.market_address

        # Ensure the tx processor is running
        await self.start_tx_processor()

        try:
            tx_hash = None
            if order.order_type == "limit":
                if not order.price:
                    raise ValueError("Price is required for limit orders")
                if not order.size:
                    raise ValueError("Size is required for limit orders")
                
                if order.side == "buy":
                    self._log_info(f"Adding buy order with price: {order.price}, size: {order.size}, post_only: {order.post_only}, tx_options: {tx_options}")
                    tx_hash = await self.orderbook.add_buy_order(
                        price=order.price,
                        size=order.size,
                        post_only=order.post_only,
                        tick_normalization=order.tick_normalization,
                        tx_options=tx_options,
                        async_execution=async_execution
                    )
                else:  # sell
                    tx_hash = await self.orderbook.add_sell_order(
                        price=order.price,
                        size=order.size,
                        post_only=order.post_only,
                        tick_normalization=order.tick_normalization,
                        tx_options=tx_options,
                        async_execution=async_execution
                    )
            elif order.order_type == "market":
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
                        tx_options=tx_options,
                        async_execution=async_execution
                    )
                else:  # sell
                    tx_hash = await self.orderbook.market_sell(
                        size=order.size,
                        min_amount_out=order.min_amount_out,
                        is_margin=order.is_margin,
                        fill_or_kill=order.fill_or_kill,
                        tx_options=tx_options,
                        async_execution=async_execution
                    )
            elif order.order_type == "cancel":
                cancel_cloid = await self.cancel_orders(
                    market_address=market_address,
                    cloids=[cloid],
                    tx_options=tx_options,
                    callback=callback, 
                    callback_args=callback_args,
                    async_execution=async_execution
                )
                return cancel_cloid

            # If we used a placeholder cloid, update it now with tx_hash_side_price format
            if order.cloid == "pending_cloid_":
                price_str = str(order.price) if order.price else "market"
                order.cloid = f"{tx_hash}_{order.side}_{price_str}"

            # Store the callback if provided
            if callback:
                self.tx_callbacks[tx_hash] = (callback, callback_args)
            
            # Add to processing queue
            self.tx_queue.append((tx_hash, [order]))
            
            return order.cloid

        except Exception as e:
            self._log_error(f"Error placing order: {e}")
            raise
        
    async def cancel_orders(
        self,
        market_address: str,
        cloids: Optional[List[str]] = None, 
        order_ids: Optional[List[int]] = None, 
        tx_options: Optional[TxOptions] = TxOptions(),
        callback: Optional[Callable[[Any], Awaitable[None]]] = None,
        callback_args: tuple = (),
        async_execution: bool = False
    ) -> str:
        """
        Cancel orders with the given cloids or order_ids
        Returns the transaction hash without waiting for confirmation
        """
        if not (cloids or order_ids):
            raise ValueError("Either cloids or order_ids must be provided for cancel orders")
            
        # Ensure the tx processor is running
        await self.start_tx_processor()
        
        # Create cancel orders for processing
        cancel_orders = []
        if cloids:
            order_ids = []
            for cloid in cloids:
                if cloid in self.cloid_to_order_id:
                    order_ids.append(self.cloid_to_order_id[cloid])
                    # Create a cancel order for tracking
                    cancel_order = OrderRequest(
                        market_address=market_address,
                        cloid=cloid,
                        order_type="cancel",
                        cancel_order_ids=[self.cloid_to_order_id[cloid]]
                    )
                    cancel_orders.append(cancel_order)
                else:
                    raise ValueError(f"Order ID not found for cloid: {cloid}")
        
        tx_hash = await self.orderbook.batch_orders(
            order_ids_to_cancel=order_ids, 
            tx_options=tx_options,
            async_execution=async_execution
        )
        
        # Store the callback if provided
        if callback:
            self.tx_callbacks[tx_hash] = (callback, callback_args)
        
        # Add to processing queue
        self.tx_queue.append((tx_hash, cancel_orders))
        
        return tx_hash
    
    async def batch_orders(
        self,
        orders: List[OrderRequest],
        tx_options: Optional[TxOptions] = TxOptions(),
        callback: Optional[Callable[[Any, List[OrderRequest]], Awaitable[None]]] = None,
        callback_args: tuple = (),
        async_execution: bool = False
    ) -> List[str]:
        """
        Place multiple orders in a single transaction without waiting for confirmation
        Returns a list of cloids for all orders
        """
        buy_prices = []
        buy_sizes = []
        sell_prices = []
        sell_sizes = []
        order_ids_to_cancel = []
        post_only = False
        
        # Ensure the tx processor is running
        await self.start_tx_processor()

        # Process order details
        for i, order in enumerate(orders):
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
            
            # Generate cloid if not provided (only for non-cancel orders)
            if not order.cloid:
                order.cloid = f"pending_cloid_{i}"
            
            # Store the order (only for non-cancel orders)
            self.cloid_to_order[order.cloid] = order
            
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
            tx_options=tx_options,
            async_execution=async_execution
        )

        # Update cloids for orders with pending cloids
        cloids = []
        
        for i, order in enumerate(orders):
            # Skip cancel orders when collecting cloids
            if order.order_type == "cancel":
                continue
            
            if order.cloid.startswith("pending_cloid_"):
                price_str = str(order.price) if order.price else "market"
                new_cloid = f"{tx_hash}_{order.side}_{price_str}"
                
                # Update all references to the old cloid
                self.cloid_to_order[new_cloid] = self.cloid_to_order.pop(order.cloid)
                order.cloid = new_cloid
            
            cloids.append(order.cloid)

        # Store the callback if provided
        if callback:
            self.tx_callbacks[tx_hash] = (callback, callback_args)
        
        # Add to processing queue - include all orders for processing
        self.tx_queue.append((tx_hash, orders))
        
        return cloids

    def match_orders_with_events(self, orders: List[OrderRequest], events: List[OrderCreatedEvent]) -> List[OrderRequest]:
        """
        Match orders with events based the price and isBuy field
        """

        for order in orders:
            if order.order_type == "cancel" or order.order_type == "market":
                continue
            for event in events:
                # Convert order.price to a number before comparison
                order_price = float(order.price) if order.price else 0
                if order_price * self.orderbook.market_params.price_precision == event.price and order.side == ("buy" if event.is_buy else "sell"):
                    self.cloid_to_order_id[order.cloid] = event.order_id
                    self.order_id_to_cloid[event.order_id] = order.cloid
                    self.cloid_to_order[order.cloid] = order
    
    
    async def get_l2_book(self):
        return await self.orderbook.get_l2_book()
    
    def get_order_by_cloid(self, cloid: str) -> OrderRequest:
        self._log_info(self.cloid_to_order_id)
        return self.cloid_to_order.get(cloid)
    
    def get_order_id_by_cloid(self, cloid: str) -> int:
        return self.cloid_to_order_id.get(cloid)

    def get_cloid_by_order_id(self, order_id: int) -> str:
        return self.order_id_to_cloid.get(order_id)

    ## Kuru API
    async def get_order_history(self, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> OrderResponse:
        return self.kuru_api.get_order_history(self.market_address, self.wallet_address, start_timestamp, end_timestamp)
    
    async def get_trades(self, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> TradeResponse:
        return self.kuru_api.get_trades(self.market_address, self.wallet_address, start_timestamp, end_timestamp)
    
    async def get_orders_by_ids(self, order_ids: List[int]) -> OrderResponse:
        return self.kuru_api.get_orders_by_ids(self.market_address, order_ids)

    async def get_orders_by_cloids(self, cloids: List[str]) -> OrderResponse:
        order_ids = [self.cloid_to_order_id[cloid] for cloid in cloids]
        return self.get_orders_by_ids(order_ids)
    
    async def get_user_orders(self) -> OrderResponse:
        return self.kuru_api.get_user_orders(self.wallet_address)

    def _log_info(self, message):
        """Log info message if logger is enabled"""
        if self.logger:
            self.logger.info(message)
    
    def _log_error(self, message):
        """Log error message if logger is enabled"""
        if self.logger:
            self.logger.error(message)
