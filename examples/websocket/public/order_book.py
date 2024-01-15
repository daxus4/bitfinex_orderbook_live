# python -c "import examples.websocket.public.order_book"

import zlib
from collections import OrderedDict
from decimal import Decimal
from math import floor, log10
from typing import Any, Dict, List, cast
import json
from copy import deepcopy

from bfxapi import Client
from bfxapi.types import TradingPairBook
from bfxapi.websocket.subscriptions import Book


def _format_float(value: float) -> str:
    """
    Format float numbers into a string compatible with the Bitfinex API.
    """

    def _find_exp(number: float) -> int:
        base10 = log10(abs(number))

        return floor(base10)

    if _find_exp(value) >= -6:
        return format(Decimal(repr(value)), "f")

    return str(value).replace("e-0", "e-")


class OrderBook:
    def __init__(self):
        self.__order_book = {"bids": OrderedDict(), "asks": OrderedDict()}

    def update(self, data: TradingPairBook) -> None:
        price, count, amount = data.price, data.count, data.amount

        kind = "bids" if amount > 0 else "asks"

        if count > 0:
            self.__order_book[kind][price] = {
                "p": price,
                "c": count,
                "a": amount,
            }

        if count == 0:
            if price in self.__order_book[kind]:
                del self.__order_book[kind][price]

    def verify(self, checksum: int) -> bool:
        values: List[int] = []

        bids = sorted(
            [
                (data["p"], data["c"], data["a"])
                for _, data in self.__order_book["bids"].items()
            ],
            key=lambda data: -data[0],
        )

        asks = sorted(
            [
                (data["p"], data["c"], data["a"])
                for _, data in self.__order_book["asks"].items()
            ],
            key=lambda data: data[0],
        )

        if len(bids) < 25 or len(asks) < 25:
            raise AssertionError("Not enough bids or asks (need at least 25).")

        for _i in range(25):
            bid, ask = bids[_i], asks[_i]
            values.extend([bid[0], bid[2]])
            values.extend([ask[0], ask[2]])

        local = ":".join(_format_float(value) for value in values)

        crc32 = zlib.crc32(local.encode("UTF-8"))

        return crc32 == checksum

    def is_verifiable(self) -> bool:
        return (
            len(self.__order_book["bids"]) >= 25
            and len(self.__order_book["asks"]) >= 25
        )

    def clear(self) -> None:
        self.__order_book = {"bids": OrderedDict(), "asks": OrderedDict()}


SYMBOL = "tBTCUSD"
SECONDS_RECORDING_DURATION = 3300
order_book = OrderBook()

bfx = Client()
timestamp_orderbook_update_map = dict()
last_checksum_timestamp = 0
starting_timestamp = 0
ending_timestamp = 0
are_new_messages_to_drop = False


@bfx.wss.on("open")
async def on_open():
    await bfx.wss.subscribe("book", symbol=SYMBOL, prec="P0", len="25")


@bfx.wss.on("subscribed")
def on_subscribed(subscription):
    print(f"Subscription successful for symbol <{subscription['symbol']}>")


@bfx.wss.on("t_book_snapshot")
def on_t_book_snapshot(
    subscription: Book, snapshot: List[TradingPairBook], timestamp: int
):
    global starting_timestamp
    global ending_timestamp
    global are_new_messages_to_drop

    starting_timestamp = timestamp
    ending_timestamp = starting_timestamp + int(SECONDS_RECORDING_DURATION * 1e3)
    are_new_messages_to_drop = False

    for data in snapshot:
        order_book.update(data)
    timestamp_orderbook_update_map[timestamp] = deepcopy(
        order_book._OrderBook__order_book
    )


@bfx.wss.on("t_book_update")
async def on_t_book_update(subscription: Book, data: TradingPairBook, timestamp: int):
    if are_new_messages_to_drop:
        return

    order_book.update(data)

    if timestamp in timestamp_orderbook_update_map:
        timestamp_orderbook_update_map[timestamp]["p"].append(data.price)
        timestamp_orderbook_update_map[timestamp]["a"].append(data.amount)
        timestamp_orderbook_update_map[timestamp]["c"].append(data.count)

    else:
        timestamp_orderbook_update_map[timestamp] = {
            "p": [data.price],
            "a": [data.amount],
            "c": [data.count],
        }

    if timestamp >= ending_timestamp:
        timestamp_orderbook_update_map[-1] = deepcopy(order_book._OrderBook__order_book)

        save_orderbook_messages_to_file(timestamp)

        await _reset_connection(subscription)


def save_orderbook_messages_to_file(timestamp: int, is_interrupted: bool = False):
    path = (
        f"data/data_{timestamp}_interrupted.json"
        if is_interrupted
        else f"data/data_{timestamp}.json"
    )

    with open(path, "w") as json_file:
        json.dump(timestamp_orderbook_update_map, json_file)


@bfx.wss.on("checksum")
async def on_checksum(subscription: Book, value: int, timestamp: int):
    global last_checksum_timestamp
    global timestamp_orderbook_update_map

    if order_book.is_verifiable():
        if not order_book.verify(value):
            print(
                "Mismatch between local and remote checksums: " + f"restarting book..."
            )

            timestamp_orderbook_update_map = _get_orderbook_updates_until(
                timestamp_orderbook_update_map, last_checksum_timestamp
            )

            save_orderbook_messages_to_file(
                last_checksum_timestamp, is_interrupted=True
            )

            await _reset_connection(subscription)
        else:
            last_checksum_timestamp = timestamp


def _get_orderbook_updates_until(timestamp_orderbook_update_map: Dict, timestamp: int):
    return {k: v for k, v in timestamp_orderbook_update_map.items() if k <= timestamp}


async def _reset_connection(subscription):
    global are_new_messages_to_drop
    are_new_messages_to_drop = True

    _subscription = cast(Dict[str, Any], subscription.copy())

    timestamp_orderbook_update_map.clear()

    await bfx.wss.unsubscribe(sub_id=_subscription.pop("sub_id"))
    print("ME STO A ISCRIVERE")
    await bfx.wss.subscribe(**_subscription)
    order_book.clear()


if __name__ == "__main__":
    bfx.wss.run()
