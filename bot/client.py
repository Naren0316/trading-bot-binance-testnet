"""
Thin wrapper around python-binance's Futures REST API, pointed at the
Binance Futures Testnet (USDT-M).

This is the only module that talks to the network. Keeping it isolated
means orders.py / cli.py never need to know about python-binance
specifics, and it's the single place that logs raw requests/responses.
"""

from typing import Optional

from binance import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from bot.logging_config import get_logger

logger = get_logger("client")

FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class TradingClientError(Exception):
    """Raised for any client-level failure (network, auth, API rejection)."""


class BinanceFuturesTestnetClient:
    """
    Wraps the python-binance Client, forced onto the Futures Testnet.
    """

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise TradingClientError(
                "API key/secret not provided. Set BINANCE_API_KEY and "
                "BINANCE_API_SECRET (see README) or pass --api-key/--api-secret."
            )

        try:
            self._client = Client(api_key, api_secret, testnet=True)
            # Belt-and-braces: explicitly force the futures base URL in case
            # the installed python-binance version doesn't fully honor
            # testnet=True for futures endpoints.
            self._client.FUTURES_URL = FUTURES_TESTNET_BASE_URL + "/fapi"
            logger.debug("Initialized Binance Futures Testnet client (base_url=%s)",
                         self._client.FUTURES_URL)
        except Exception as exc:  # noqa: BLE001 - surface as our own error type
            logger.error("Failed to initialize Binance client: %s", exc)
            raise TradingClientError(f"Failed to initialize Binance client: {exc}") from exc

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """Fetch the latest mark price for a symbol (used for informational output)."""
        try:
            logger.debug("REQUEST get_symbol_ticker symbol=%s", symbol)
            ticker = self._client.futures_symbol_ticker(symbol=symbol)
            logger.debug("RESPONSE get_symbol_ticker: %s", ticker)
            return float(ticker["price"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch price for %s: %s", symbol, exc)
            return None

    def place_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        params = dict(symbol=symbol, side=side, type="MARKET", quantity=quantity)
        return self._place_order(params)

    def place_limit_order(
        self, symbol: str, side: str, quantity: float, price: float, time_in_force: str = "GTC"
    ) -> dict:
        params = dict(
            symbol=symbol,
            side=side,
            type="LIMIT",
            quantity=quantity,
            price=price,
            timeInForce=time_in_force,
        )
        return self._place_order(params)

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = "GTC",
    ) -> dict:
        params = dict(
            symbol=symbol,
            side=side,
            type="STOP",
            quantity=quantity,
            price=price,
            stopPrice=stop_price,
            timeInForce=time_in_force,
        )
        return self._place_order(params)

    def _place_order(self, params: dict) -> dict:
        """
        Send an order to the Futures Testnet, logging the outgoing request
        and the raw response/error, and translating failures into
        TradingClientError so callers only need to catch one exception type.
        """
        logger.info("REQUEST futures_create_order: %s", params)
        try:
            response = self._client.futures_create_order(**params)
            logger.info("RESPONSE futures_create_order: %s", response)
            return response
        except BinanceAPIException as exc:
            # Binance rejected the request (bad symbol, insufficient margin,
            # invalid price/quantity precision, etc.)
            logger.error(
                "Binance API rejected order (code=%s, msg=%s) | params=%s",
                exc.code, exc.message, params,
            )
            raise TradingClientError(f"Binance API error {exc.code}: {exc.message}") from exc
        except BinanceRequestException as exc:
            # Malformed request / response parsing issue
            logger.error("Binance request error: %s | params=%s", exc, params)
            raise TradingClientError(f"Binance request error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - network errors, timeouts, DNS, etc.
            logger.error("Network/unexpected error placing order: %s | params=%s", exc, params)
            raise TradingClientError(f"Network or unexpected error: {exc}") from exc
