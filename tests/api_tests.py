import sys
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

import kuru_sdk.api as KuruAPI

def test_get_user_orders():
    api = KuruAPI.KuruAPI("https://api.kuru.io/api/v2")
    orders = api.get_user_orders("0xb0445315e7ab096Fa03F79ac9644895E59CB9819",)
    print(orders)

def test_get_orders_by_ids():
    api = KuruAPI.KuruAPI("https://api.kuru.io/api/v2")
    orders = api.get_orders_by_ids("0xf7f70cb1a1b1128272d1c2751ab788b1226303b1", [7,2,3])
    print(orders)

def test_get_active_orders():
    api = KuruAPI.KuruAPI("http://api.kuru.io/api/v2")
    orders = api.get_active_orders("0xb0445315e7ab096Fa03F79ac9644895E59CB9819")
    print(orders)

def test_get_order_history():
    api = KuruAPI.KuruAPI("http://api.kuru.io/api/v2")
    orders = api.get_order_history("0xb0445315e7ab096Fa03F79ac9644895E59CB9819")
    print(orders)

def test_get_trades():
    api = KuruAPI.KuruAPI("http://api.kuru.io/api/v2")
    trades = api.get_trades("0x05e6f736b5dedd60693fa806ce353156a1b73cf3", "0x6650514f909d2aB6A6a6647464E45F9f9D81F1Da")
    print(trades)

test_get_trades()