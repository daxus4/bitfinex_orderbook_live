from typing import List, Any, cast

from pyee.base import EventEmitter
import time

from bfxapi.types import serializers

from bfxapi.websocket.subscriptions import (
    Subscription,
    Ticker,
    Trades,
    Book,
    Candles,
    Status,
)

_CHECKSUM = "cs"


class PublicChannelsHandler:
    def __init__(self, event_emitter: EventEmitter) -> None:
        self.__event_emitter = event_emitter

    def handle(self, subscription: Subscription, stream: List[Any]) -> None:
        if subscription["channel"] == "ticker":
            self.__ticker_channel_handler(cast(Ticker, subscription), stream)
        elif subscription["channel"] == "trades":
            self.__trades_channel_handler(cast(Trades, subscription), stream)
        elif subscription["channel"] == "book":
            subscription = cast(Book, subscription)

            if stream[0] == _CHECKSUM:
                self.__checksum_handler(subscription, stream[1], stream[2])
            else:
                if subscription["prec"] != "R0":
                    self.__book_channel_handler(subscription, [stream[0]], stream[1])
                else:
                    self.__raw_book_channel_handler(subscription, stream)
        elif subscription["channel"] == "candles":
            self.__candles_channel_handler(cast(Candles, subscription), stream)
        elif subscription["channel"] == "status":
            self.__status_channel_handler(cast(Status, subscription), stream)

    # pylint: disable-next=inconsistent-return-statements
    def __ticker_channel_handler(self, subscription: Ticker, stream: List[Any]):
        if subscription["symbol"].startswith("t"):
            return self.__event_emitter.emit(
                "t_ticker_update",
                subscription,
                serializers.TradingPairTicker.parse(*stream[0]),
            )

        if subscription["symbol"].startswith("f"):
            return self.__event_emitter.emit(
                "f_ticker_update",
                subscription,
                serializers.FundingCurrencyTicker.parse(*stream[0]),
            )

    # pylint: disable-next=inconsistent-return-statements
    def __trades_channel_handler(self, subscription: Trades, stream: List[Any]):
        if (event := stream[0]) and event in ["te", "tu", "fte", "ftu"]:
            events = {
                "te": "t_trade_execution",
                "tu": "t_trade_execution_update",
                "fte": "f_trade_execution",
                "ftu": "f_trade_execution_update",
            }

            if subscription["symbol"].startswith("t"):
                return self.__event_emitter.emit(
                    events[event],
                    subscription,
                    serializers.TradingPairTrade.parse(*stream[1]),
                )

            if subscription["symbol"].startswith("f"):
                return self.__event_emitter.emit(
                    events[event],
                    subscription,
                    serializers.FundingCurrencyTrade.parse(*stream[1]),
                )

        if subscription["symbol"].startswith("t"):
            return self.__event_emitter.emit(
                "t_trades_snapshot",
                subscription,
                [
                    serializers.TradingPairTrade.parse(*sub_stream)
                    for sub_stream in stream[0]
                ],
            )

        if subscription["symbol"].startswith("f"):
            return self.__event_emitter.emit(
                "f_trades_snapshot",
                subscription,
                [
                    serializers.FundingCurrencyTrade.parse(*sub_stream)
                    for sub_stream in stream[0]
                ],
            )

    # pylint: disable-next=inconsistent-return-statements
    def __book_channel_handler(
        self, subscription: Book, stream: List[Any], timestamp: int
    ):
        if subscription["symbol"].startswith("t"):
            if all(isinstance(sub_stream, list) for sub_stream in stream[0]):
                return self.__event_emitter.emit(
                    "t_book_snapshot",
                    subscription,
                    [
                        serializers.TradingPairBook.parse(*sub_stream)
                        for sub_stream in stream[0]
                    ],
                    timestamp,
                )

            return self.__event_emitter.emit(
                "t_book_update",
                subscription,
                serializers.TradingPairBook.parse(*stream[0]),
                timestamp,
            )

        if subscription["symbol"].startswith("f"):
            if all(isinstance(sub_stream, list) for sub_stream in stream[0]):
                return self.__event_emitter.emit(
                    "f_book_snapshot",
                    subscription,
                    [
                        serializers.FundingCurrencyBook.parse(*sub_stream)
                        for sub_stream in stream[0]
                    ],
                )

            return self.__event_emitter.emit(
                "f_book_update",
                subscription,
                serializers.FundingCurrencyBook.parse(*stream[0]),
            )

    # pylint: disable-next=inconsistent-return-statements
    def __raw_book_channel_handler(self, subscription: Book, stream: List[Any]):
        if subscription["symbol"].startswith("t"):
            if all(isinstance(sub_stream, list) for sub_stream in stream[0]):
                return self.__event_emitter.emit(
                    "t_raw_book_snapshot",
                    subscription,
                    [
                        serializers.TradingPairRawBook.parse(*sub_stream)
                        for sub_stream in stream[0]
                    ],
                )

            return self.__event_emitter.emit(
                "t_raw_book_update",
                subscription,
                serializers.TradingPairRawBook.parse(*stream[0]),
            )

        if subscription["symbol"].startswith("f"):
            if all(isinstance(sub_stream, list) for sub_stream in stream[0]):
                return self.__event_emitter.emit(
                    "f_raw_book_snapshot",
                    subscription,
                    [
                        serializers.FundingCurrencyRawBook.parse(*sub_stream)
                        for sub_stream in stream[0]
                    ],
                )

            return self.__event_emitter.emit(
                "f_raw_book_update",
                subscription,
                serializers.FundingCurrencyRawBook.parse(*stream[0]),
            )

    # pylint: disable-next=inconsistent-return-statements
    def __candles_channel_handler(self, subscription: Candles, stream: List[Any]):
        if all(isinstance(sub_stream, list) for sub_stream in stream[0]):
            return self.__event_emitter.emit(
                "candles_snapshot",
                subscription,
                [serializers.Candle.parse(*sub_stream) for sub_stream in stream[0]],
            )

        return self.__event_emitter.emit(
            "candles_update", subscription, serializers.Candle.parse(*stream[0])
        )

    # pylint: disable-next=inconsistent-return-statements
    def __status_channel_handler(self, subscription: Status, stream: List[Any]):
        if subscription["key"].startswith("deriv:"):
            return self.__event_emitter.emit(
                "derivatives_status_update",
                subscription,
                serializers.DerivativesStatus.parse(*stream[0]),
            )

        if subscription["key"].startswith("liq:"):
            return self.__event_emitter.emit(
                "liquidation_feed_update",
                subscription,
                serializers.Liquidation.parse(*stream[0][0]),
            )

    # pylint: disable-next=inconsistent-return-statements
    def __checksum_handler(self, subscription: Book, value: int, timestamp: int):
        return self.__event_emitter.emit(
            "checksum", subscription, value & 0xFFFFFFFF, timestamp
        )
