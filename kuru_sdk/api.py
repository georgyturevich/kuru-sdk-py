import requests
from typing import List, Optional
from kuru_sdk.types import Order

class KuruAPI:
  def __init__(self, url: str):
    self.url = url

  def get_user_orders(self, user_address: str) -> List[Order]:
    response = requests.get(f"{self.url}/orders/user/{user_address}")
    return response.json()
  
  def get_active_orders(self, user_address: str) -> List[Order]:
    response = requests.get(f"{self.url}/{user_address}/user/orders/active")
    return response.json()
  
  def get_order_history(self, user_address: str) -> List[Order]:
    response = requests.get(f"{self.url}/orders/user/{user_address}")
    return response.json()
  
  def get_trades(self, market_address: str, user_address: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Order]:
    url = f"{self.url}/{market_address}/trades/user/{user_address}"
    params = {}
    if start_timestamp is not None:
      params['startTimestamp'] = start_timestamp
    if end_timestamp is not None:
      params['endTimestamp'] = end_timestamp
    response = requests.get(url, params=params)
    return response.json()

  def get_orders_by_ids(self, market_address: str, order_ids: List[int]) -> List[Order]:
    response = requests.get(f"{self.url}/orders/market/{market_address}", params={"orderIds": order_ids})
    return response.json()

  