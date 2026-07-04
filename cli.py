#!/usr/bin/env python3
"""
CLI entry point for the Simplified Trading Bot (Binance Futures Testnet).

Examples:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
    python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.01 \\
                   --price 61000 --stop-price 60500
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceFuturesTestnetClient, TradingClientError
from bot.logging_config import get_logger, setup_logging
from bot.orders import place_order
from bot.validators import ValidationError, build_order_request

logger = get_logger("cli")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place MARKET, LIMIT, or STOP_LIMIT orders on Binance Futures Testnet.",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"],
                         help="Order side")
    parser.add_argument("--type", dest="order_type", required=True,
                         choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
                         help="Order type")
    parser.add_argument("--quantity", required=True, help="Order quantity (base asset units)")
    parser.add_argument("--price", default=None,
                         help="Limit price (required for LIMIT and STOP_LIMIT)")
    parser.add_argument("--stop-price", dest="stop_price", default=None,
                         help="Stop trigger price (required for STOP_LIMIT)")
    parser.add_argument("--time-in-force", dest="time_in_force", default="GTC",
                         choices=["GTC", "IOC", "FOK"], help="Time in force (default: GTC)")
    parser.add_argument("--api-key", dest="api_key", default=None,
                         help="Binance Testnet API key (overrides BINANCE_API_KEY env var)")
    parser.add_argument("--api-secret", dest="api_secret", default=None,
                         help="Binance Testnet API secret (overrides BINANCE_API_SECRET env var)")
    return parser.parse_args(argv)


def print_order_summary(request) -> None:
    print("\n" + "=" * 50)
    print("ORDER REQUEST SUMMARY")
    print("=" * 50)
    print(f"  Symbol       : {request.symbol}")
    print(f"  Side         : {request.side}")
    print(f"  Type         : {request.order_type}")
    print(f"  Quantity     : {request.quantity}")
    if request.price is not None:
        print(f"  Price        : {request.price}")
    if request.stop_price is not None:
        print(f"  Stop Price   : {request.stop_price}")
    if request.order_type != "MARKET":
        print(f"  Time In Force: {request.time_in_force}")
    print("=" * 50)


def print_order_result(result) -> None:
    print("\n" + "-" * 50)
    print("ORDER RESPONSE")
    print("-" * 50)
    if result.success:
        print(f"  Order ID      : {result.order_id}")
        print(f"  Status        : {result.status}")
        print(f"  Executed Qty  : {result.executed_qty}")
        print(f"  Avg Price     : {result.avg_price or 'N/A (order not yet filled)'}")
        print("-" * 50)
        print("SUCCESS: order placed on Binance Futures Testnet.")
    else:
        print(f"  Error: {result.error_message}")
        print("-" * 50)
        print("FAILED: order was not placed.")
    print("-" * 50 + "\n")


def main(argv=None) -> int:
    load_dotenv()
    setup_logging()

    args = parse_args(argv)

    # 1. Validate input
    try:
        request = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        logger.error("Input validation failed: %s", exc)
        print(f"\nInvalid input: {exc}\n")
        return 1

    print_order_summary(request)

    # 2. Build client
    api_key = args.api_key or os.getenv("BINANCE_API_KEY")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET")

    try:
        client = BinanceFuturesTestnetClient(api_key, api_secret)
    except TradingClientError as exc:
        logger.error("Client initialization failed: %s", exc)
        print(f"\nCould not initialize client: {exc}\n")
        return 1

    # 3. Place order (never raises; failures come back in result)
    result = place_order(client, request)
    print_order_result(result)

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
