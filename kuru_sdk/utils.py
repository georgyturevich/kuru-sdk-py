
from dataclasses import dataclass
from kuru_sdk.orderbook import Orderbook
from kuru_sdk.types import OrderCreatedEvent
def get_order_id_from_receipt(orderbook: Orderbook, receipt) -> int | None:
    """
    Get the order id by decoding the OrderCreated event from the transaction receipt logs.

    Args:
        orderbook: The Orderbook instance containing the contract object.
        receipt: The transaction receipt obtained from web3.eth.wait_for_transaction_receipt.

    Returns:
        The order ID if an OrderCreated event is found, otherwise None.
    """
    # Assuming the event name in your contract is 'OrderCreated'
    # Access the contract instance from the orderbook
    contract = orderbook.contract

    try:
        # Process the receipt to find 'OrderCreated' events
        decoded_logs = contract.events.OrderCreated().process_receipt(receipt)

        if decoded_logs:
            # Assuming the first OrderCreated event contains the relevant orderId
            order_id = decoded_logs[0]['args']['orderId']
            return order_id
        else:
            print("No OrderCreated event found in the transaction receipt.")
            return None
    except Exception as e:
        # Handle potential errors during decoding (e.g., event not found in ABI)
        print(f"Error decoding logs from receipt: {e}")
        return None


def decode_logs(orderbook: Orderbook, receipt) -> list[OrderCreatedEvent]:
    contract = orderbook.contract
    tx_logs = receipt.get('logs')
    order_created_events = []
    for log in tx_logs:
        try:
            order_created_event = contract.events.OrderCreated().process_log(log)
            print(f"Order created event: {order_created_event}")
            if order_created_event:
              order_created_event = OrderCreatedEvent(
                  order_id=order_created_event['args']['orderId'],
                  price=order_created_event['args']['price'],
                  size=order_created_event['args']['size'],
                  is_buy=order_created_event['args']['isBuy']
                  )
              order_created_events.append(order_created_event)
        except Exception as e:
            print(f"Error decoding logs for order created event: {e}")
            continue

    return order_created_events


