from web3 import Web3

from kuru_sdk.utils import OrderCreatedEvent
from .orderbook import Orderbook, TxOptions
from .utils import decode_logs, get_order_id_from_receipt
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from kuru_sdk.types import OrderRequest


class ClientOrderExecutor:
    def __init__(self,
                 web3: Web3,
                 contract_address: str,
                 private_key: str):
        self.web3 = web3
        self.orderbook = Orderbook(web3, contract_address, private_key)
        # storage dicts
        self.cloid_to_order_id: Dict[str, int] = {}
        self.cloid_to_order: Dict[str, OrderRequest] = {}


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

            # Wait for the transaction receipt using the web3 instance from the orderbook
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Order receipt: {receipt}")

            if receipt.status == 1:
                if cloid:
                    order_id = get_order_id_from_receipt(self.orderbook, receipt)
                    print(f"Order ID: {order_id}")
                    if order_id:
                        self.cloid_to_order_id[cloid] = order_id
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
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
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

        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

        print(f"Batch order receipt: {receipt}")

        if receipt.status == 1:
            order_created_events = decode_logs(self.orderbook, receipt)
            self.match_orders_with_events(orders, order_created_events)
            print(f"Transaction successful for batch orders, tx_hash: {receipt.transactionHash.hex()}")
            print(f"Order IDs: {self.cloid_to_order_id}")
            return receipt.transactionHash.hex()
        else:
            raise Exception(f"Batch order failed: Transaction status {receipt.status}, receipt: {receipt}")
        

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

    ## Websocket handlers
    async def on_order_created_handler(self, payload):
        print(f"Order created: {payload}")

    async def on_trade_handler(self, payload):
        print(f"Trade: {payload}")
        
    async def on_order_cancelled_handler(self, payload):
        print(f"Order cancelled: {payload}")
        
        
        
        