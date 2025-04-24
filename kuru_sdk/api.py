import aiohttp
from typing import List, Optional
from kuru_sdk.types import Order

class KuruAPI:
  def __init__(self, url: str):
    self.url = url
    self.session = None

  async def _ensure_session(self):
    """Ensure an aiohttp session exists or create one"""
    if self.session is None or self.session.closed:
      self.session = aiohttp.ClientSession()
    return self.session

  async def get_user_orders(self, user_address: str) -> List[Order]:
    session = await self._ensure_session()
    async with session.get(f"{self.url}/orders/user/{user_address}") as response:
      return await response.json()
  
  async def get_active_orders(self, user_address: str) -> List[Order]:
    session = await self._ensure_session()
    async with session.get(f"{self.url}/{user_address}/user/orders/active") as response:
      return await response.json()
  
  async def get_order_history(self, user_address: str) -> List[Order]:
    session = await self._ensure_session()
    async with session.get(f"{self.url}/orders/user/{user_address}") as response:
      return await response.json()
  
  async def get_trades(self, market_address: str, user_address: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Order]:
    url = f"{self.url}/{market_address}/trades/user/{user_address}"
    params = {}
    if start_timestamp is not None:
      params['startTimestamp'] = start_timestamp
    if end_timestamp is not None:
      params['endTimestamp'] = end_timestamp
    
    session = await self._ensure_session()
    async with session.get(url, params=params) as response:
      return await response.json()

  async def get_orders_by_ids(self, market_address: str, order_ids: List[int]) -> List[Order]:
    session = await self._ensure_session()
    async with session.get(
      f"{self.url}/orders/market/{market_address}", 
      params={"orderIds": order_ids}
    ) as response:
      return await response.json()
      
  async def close(self):
    """Close the underlying aiohttp session"""
    if self.session and not self.session.closed:
      await self.session.close()

  