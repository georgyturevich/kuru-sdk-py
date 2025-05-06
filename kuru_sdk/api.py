import requests
from typing import List, Optional
from datetime import datetime
from kuru_sdk.types import Order, OrderResponse, TradeResponse, Trade

class KuruAPI:
    def __init__(self, url: str):
      self.url = url

    def get_user_orders(self, user_address: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Order]:
        response = requests.get(f"{self.url}/orders/user/{user_address}", params={"limit": limit, "offset": offset})
        response_json = response.json()
        
        if isinstance(response_json, dict) and 'data' in response_json and 'data' in response_json['data']:
            orders_data = response_json['data']['data']
            return [Order(
                market_address=order['marketAddress'],
                order_id=order['orderid'],
                owner=order['owner'],
                size=order['size'],
                price=order['price'],
                is_buy=order['isbuy'],
                remaining_size=order['remainingsize'],
                is_canceled=order['iscanceled'],
                block_number=order['blocknumber'],
                tx_index=order['txindex'],
                log_index=order['logindex'],
                transaction_hash=order['transactionhash'],
                trigger_time=order['triggertime'],
                total_size=order['size']  # Using size as total_size since it's not in the response
            ) for order in orders_data]
        return []

    def get_active_orders(self, user_address: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Order]:
        response = requests.get(f"{self.url}/{user_address}/user/orders/active", params={"limit": limit, "offset": offset})
        response_json = response.json()
        
        if isinstance(response_json, dict) and 'data' in response_json and 'data' in response_json['data']:
            orders_data = response_json['data']['data']
            return [Order(
                market_address=order['marketAddress'],
                order_id=order['orderid'],
                owner=order['owner'],
                size=order['size'],
                price=order['price'],
                is_buy=order['isbuy'],
                remaining_size=order['remainingsize'],
                is_canceled=order['iscanceled'],
                block_number=order['blocknumber'],
                tx_index=order['txindex'],
                log_index=order['logindex'],
                transaction_hash=order['transactionhash'],
                trigger_time=order['triggertime'],
                total_size=order['size']  # Using size as total_size since it's not in the response
            ) for order in orders_data]
        return []

    def get_trades(self, market_address: str, user_address: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Trade]:
        url = f"{self.url}/{market_address}/trades/user/{user_address}"
        params = {}
        if start_timestamp is not None:
            params['startTimestamp'] = start_timestamp
        if end_timestamp is not None:
            params['endTimestamp'] = end_timestamp
        response = requests.get(url, params=params)
        response_json = response.json()
        
        if isinstance(response_json, dict) and 'data' in response_json and 'data' in response_json['data']:
            trades_data = response_json['data']['data']
            return [Trade(
                orderid=trade['orderid'],
                makeraddress=trade['makeraddress'],
                takeraddress=trade['takeraddress'],
                isbuy=trade['isbuy'],
                price=trade['price'],
                filledsize=trade['filledsize'],
                blocknumber=trade['blocknumber'],
                txindex=trade['txindex'],
                logindex=trade['logindex'],
                transactionhash=trade['transactionhash'],
                triggertime=trade['triggertime'],
                monadPrice=trade.get('monadPrice', 0.0)  # Default to 0.0 if not present
            ) for trade in trades_data]
        return []

    def get_orders_by_ids(self, market_address: str, order_ids: List[int]) -> List[Order]:
        response = requests.get(f"{self.url}/orders/market/{market_address}", params={"orderIds": order_ids})
        response_json = response.json()
        
        if isinstance(response_json, dict) and 'data' in response_json and 'data' in response_json['data']:
            orders_data = response_json['data']['data']
            return [Order(
                market_address=order['marketAddress'],
                order_id=order['orderid'],
                owner=order['owner'],
                size=order['size'],
                price=order['price'],
                is_buy=order['isbuy'],
                remaining_size=order['remainingsize'],
                is_canceled=order['iscanceled'],
                block_number=order['blocknumber'],
                tx_index=order['txindex'],
                log_index=order['logindex'],
                transaction_hash=order['transactionhash'],
                trigger_time=order['triggertime'],
                total_size=order['size']  # Using size as total_size since it's not in the response
            ) for order in orders_data]
        return []

    def get_orders_by_sdk_cloid(self, market_address: str, user_address: str, client_order_ids: List[str]) -> List[Order]:
        formatted_client_order_ids = ['0x' + cloid if not cloid.startswith('0x') else cloid for cloid in client_order_ids]

        request_body = {
            "clientOrderIds": formatted_client_order_ids,
            "marketAddress": market_address,
            "userAddress": user_address
        }
        response = requests.post(f"{self.url}/orders/client", json=request_body)
        response_json = response.json()
        
        if isinstance(response_json, dict) and 'data' in response_json and 'data' in response_json['data']:
            orders_data = response_json['data']['data']
            return [Order(
                market_address=order['marketAddress'],
                order_id=order['orderid'],
                owner=order['owner'],
                size=order['size'],
                price=order['price'],
                is_buy=order['isbuy'],
                remaining_size=order['remainingsize'],
                is_canceled=order['iscanceled'],
                block_number=order['blocknumber'],
                tx_index=order['txindex'],
                log_index=order['logindex'],
                transaction_hash=order['transactionhash'],
                trigger_time=order['triggertime'],
                total_size=order['size']  # Using size as total_size since it's not in the response
            ) for order in orders_data]
        return []
