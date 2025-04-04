from web3 import Web3

from kuru_sdk.utils import OrderCreatedEvent
from .orderbook import Orderbook, TxOptions
from .utils import decode_logs, get_order_id_from_receipt
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass

@dataclass
class OrderRequest:
    market_address: str
    order_type: Literal["limit", "market", "cancel"]
    side: Optional[Literal["buy", "sell"]] = None # optional for cancel orders
    price: Optional[str] = None  # Optional for market orders
    size: Optional[str] = None # optional for cancel orders
    post_only: Optional[bool] = None 
    is_margin: Optional[bool] = False 
    fill_or_kill: Optional[bool] = False
    min_amount_out: Optional[str] = None  # For market orders
    cancel_order_ids: Optional[List[int | str]] = None # For batch cancel
    cancel_cloids: Optional[List[str]] = None
    cloid: Optional[str] = None
    tick_normalization: Optional[str] = None


class ClientOrderExecutor:
    def __init__(self,
                 web3: Web3,
                 contract_address: str,
                 private_key: str):
        self.web3 = web3
        self.orderbook = Orderbook(web3, contract_address, private_key)
        # storage dicts
        self.cloid_to_order_id: Dict[str, int] = {}

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
                if not (order.cancel_order_ids or order.cancel_cloids):
                    raise ValueError("Either cancel_order_ids or cancel_cloids must be provided for cancel orders")
                
                if order.cancel_order_ids:
                    print(f"Cancelling orders with IDs: {order.cancel_order_ids}")
                    tx_hash = await self.orderbook.batch_orders(order_ids_to_cancel=order.cancel_order_ids, tx_options=tx_options)
                elif order.cancel_cloids:
                    order_ids = [self.cloid_to_order_id[cloid] for cloid in order.cancel_cloids]
                    tx_hash = await self.orderbook.batch_orders(order_ids_to_cancel=order_ids, tx_options=tx_options)

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
                    order_ids_to_cancel.extend([self.cloid_to_order_id[cloid] for cloid in order.cancel_cloids])
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

        print(f"Events: {events}")

        print(f"Orders: {orders}")

        for order in orders:
            if order.order_type == "cancel" or order.order_type == "market":
                continue
            for event in events:
                if order.price * self.orderbook.market_params.price_precision == event.price and order.side == ("buy" if event.is_buy else "sell"):
                    self.cloid_to_order_id[order.cloid] = event.order_id