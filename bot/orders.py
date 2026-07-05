"""
Order placement logic: takes a validated OrderRequest, dispatches to the
right client method, and normalizes the response into an OrderResult
that's easy for the CLI layer to print.
"""

from dataclasses import dataclass
from typing import Optional

from bot.client import BinanceFuturesTestnetClient, TradingClientError
from bot.logging_config import get_logger
from bot.validators import OrderRequest

logger = get_logger("orders")


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    raw_response: Optional[dict] = None
    error_message: Optional[str] = None


def place_order(client: BinanceFuturesTestnetClient, request: OrderRequest) -> OrderResult:
    """
    Execute the given OrderRequest against the Futures Testnet and return
    a normalized OrderResult. Never raises: all failures are captured in
    OrderResult.success / error_message so the CLI can print a clean
    success/failure message either way.
    """
    logger.info(
        "Placing %s %s order | symbol=%s qty=%s price=%s stop_price=%s",
        request.order_type, request.side, request.symbol,
        request.quantity, request.price, request.stop_price,
    )

    try:
        if request.order_type == "MARKET":
            response = client.place_market_order(
                symbol=request.symbol, side=request.side, quantity=request.quantity
            )
        elif request.order_type == "LIMIT":
            response = client.place_limit_order(
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                price=request.price,
                time_in_force=request.time_in_force,
            )
        elif request.order_type == "STOP_LIMIT":
            response = client.place_stop_limit_order(
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                price=request.price,
                stop_price=request.stop_price,
                time_in_force=request.time_in_force,
            )
        else:
            # Should be unreachable if validators.py did its job.
            raise TradingClientError(f"Unsupported order type: {request.order_type}")

        result = OrderResult(
            success=True,
            order_id=response.get("orderId"),
            status=response.get("status"),
            executed_qty=response.get("executedQty"),
            avg_price=response.get("avgPrice"),
            raw_response=response,
        )
        logger.info("Order placed successfully: orderId=%s status=%s",
                    result.order_id, result.status)
        return result

    except TradingClientError as exc:
        logger.error("Order failed: %s", exc)
        return OrderResult(success=False, error_message=str(exc))
