import sys
import asyncio
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

import kuru_sdk.api as KuruAPI

async def test_get_user_orders():
    api = KuruAPI.KuruAPI("https://api.testnet.kuru.io/api/v2")
    try:
        orders = await api.get_user_orders("0xf7f70cb1a1b1128272d1c2751ab788b1226303b1")
        print(orders)
    finally:
        await api.close()

async def test_get_orders_by_ids():
    api = KuruAPI.KuruAPI("http://localhost:3000/api/v2")
    try:
        orders = await api.get_orders_by_ids("0x8de88cf2bc9b8591fa547dd38775bc83361f8b4e", [7,2,3])
        print(orders)
    finally:
        await api.close()

async def test_get_active_orders():
    api = KuruAPI.KuruAPI("http://api.kuru.io/api/v2")
    try:
        orders = await api.get_active_orders("0xf7f70cb1a1b1128272d1c2751ab788b1226303b1")
        print(orders)
    finally:
        await api.close()

async def test_get_order_history():
    api = KuruAPI.KuruAPI("http://api.kuru.io/api/v2")
    try:
        orders = await api.get_order_history("0xf7f70cb1a1b1128272d1c2751ab788b1226303b1")
        print(orders)
    finally:
        await api.close()

async def test_get_trades():
    api = KuruAPI.KuruAPI("http://api.kuru.io/api/v2")
    try:
        trades = await api.get_trades("0x05e6f736b5dedd60693fa806ce353156a1b73cf3", "0xf7f70cb1a1b1128272d1c2751ab788b1226303b1")
        print(trades)
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(test_get_trades())