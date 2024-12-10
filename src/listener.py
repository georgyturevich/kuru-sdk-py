from web3 import Web3
from web3.contract import Contract
from typing import Callable, Dict, Any

class MarketListener:
    def __init__(self, rpc_url: str, contract_address: str, abi: Dict[str, Any]):
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = self.web3.eth.contract(address=contract_address, abi=abi)

    def listen_for_orders(self, callback: Callable[[Dict[str, Any]], None]):
        event_filter = self.contract.events.OrderCreated.createFilter(fromBlock='latest')
        while True:
            for event in event_filter.get_new_entries():
                order_event = {
                    'orderId': event.args.orderId,
                    'ownerAddress': event.args.ownerAddress,
                    'size': event.args.size,
                    'price': event.args.price,
                    'isBuy': event.args.isBuy
                }
                callback(order_event)

    def listen_for_trades(self, callback: Callable[[Dict[str, Any]], None]):
        event_filter = self.contract.events.Trade.createFilter(fromBlock='latest')
        while True:
            for event in event_filter.get_new_entries():
                trade_event = {
                    'orderId': event.args.orderId,
                    'isBuy': event.args.isBuy,
                    'price': event.args.price,
                    'updatedSize': event.args.updatedSize,
                    'takerAddress': event.args.takerAddress,
                    'filledSize': event.args.filledSize
                }
                callback(trade_event)
