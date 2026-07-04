# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application for placing MARKET, LIMIT, and
STOP_LIMIT orders on the Binance USDT-M Futures Testnet, with input
validation, structured logging, and clean error handling.

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance Futures Testnet API wrapper (only module that hits the network)
    orders.py          # Order placement / response normalization
    validators.py      # CLI input validation
    logging_config.py  # Rotating file + console logging setup
  cli.py                # CLI entry point (argparse)
  logs/
    trading_bot.log     # Created at runtime — request/response/error log
  requirements.txt
  .env.example
  README.md
```

## 1. Setup

### 1.1 Create a Futures Testnet account and API key

1. Go to https://testnet.binancefuture.com and log in with a GitHub account
   (this is separate from a regular Binance account and from the Spot
   Testnet).
2. Once logged in, generate an **API Key** and **Secret** from the API Key
   panel on the testnet site.
3. The testnet gives you a virtual USDT balance automatically — no real
   funds are involved anywhere in this project.

### 1.2 Install dependencies

Requires Python 3.9+.

```bash
cd trading_bot
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.3 Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and paste in your testnet API key/secret:

```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

Credentials can alternatively be passed directly via `--api-key` /
`--api-secret` flags, which override the `.env` values.

## 2. Running the bot

All commands are run from the `trading_bot/` directory.

### Market order (BUY)

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order (SELL)

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
```

### Stop-Limit order (bonus third order type)

```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.01 \
    --price 61000 --stop-price 60500
```

### CLI arguments

| Flag              | Required             | Notes                                   |
|-------------------|-----------------------|------------------------------------------|
| `--symbol`        | yes                   | e.g. `BTCUSDT`                          |
| `--side`           | yes                   | `BUY` or `SELL`                         |
| `--type`           | yes                   | `MARKET`, `LIMIT`, or `STOP_LIMIT`      |
| `--quantity`       | yes                   | base asset quantity, must be > 0        |
| `--price`          | LIMIT / STOP_LIMIT only | limit price                          |
| `--stop-price`     | STOP_LIMIT only       | trigger price                           |
| `--time-in-force`  | no (default `GTC`)    | `GTC`, `IOC`, or `FOK`                  |
| `--api-key`        | no                    | overrides `BINANCE_API_KEY` env var     |
| `--api-secret`     | no                    | overrides `BINANCE_API_SECRET` env var  |

Invalid combinations (e.g. `MARKET` with `--price`, or `LIMIT` without
`--price`) are rejected before any network call is made, with a clear
error message.

## 3. Output

Every run prints:

1. **Order request summary** — the parameters about to be sent.
2. **Order response** — `orderId`, `status`, `executedQty`, `avgPrice`
   (or an error message on failure).
3. A final `SUCCESS` / `FAILED` line.

Example:

```
==================================================
ORDER REQUEST SUMMARY
==================================================
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Quantity     : 0.01
==================================================

--------------------------------------------------
ORDER RESPONSE
--------------------------------------------------
  Order ID      : 3702819
  Status        : FILLED
  Executed Qty  : 0.010
  Avg Price     : 60123.40
--------------------------------------------------
SUCCESS: order placed on Binance Futures Testnet.
--------------------------------------------------
```

## 4. Logging

All requests, raw API responses, and errors are logged to
`logs/trading_bot.log` (rotated at 2MB, 5 backups kept). The console only
shows INFO-level messages; the file captures full DEBUG-level detail,
including exact request parameters and raw JSON responses, so no
credentials-free troubleshooting info is lost.

## 5. Error handling

- **Invalid input** (bad symbol format, unsupported side/type, missing
  price for LIMIT, non-positive quantity, etc.) is caught by
  `bot/validators.py` before any API call, and reported clearly.
- **API errors** (bad symbol, insufficient testnet balance, precision/
  filter violations, etc.) are caught around the `python-binance` call in
  `bot/client.py`, logged with the Binance error code/message, and
  surfaced as a `FAILED` result rather than a stack trace.
- **Network failures** (timeouts, DNS errors, connection resets) are
  caught by the same layer and reported the same way.

## 6. Assumptions

- Futures Testnet **API keys are separate** from Spot Testnet and from a
  real Binance account; you must generate them specifically at
  https://testnet.binancefuture.com.
- The account must have a testnet USDT balance and, in most cases, the
  target symbol's leverage/margin mode already configured on the testnet
  UI before an order will fill successfully (this is a Binance account
  setting, not something the script manages).
- Quantity/price precision (tick size, step size) for each symbol follows
  Binance's exchange filters; if you place an order with a quantity/price
  that violates a symbol's filter, Binance's API will reject it and the
  bot will report that as a `FAILED` order with the underlying Binance
  error message — the bot does not attempt to auto-round values.
- `STOP_LIMIT` is implemented as Binance Futures' `STOP` order type
  (limit order that activates once `stopPrice` is touched), which is the
  standard USDT-M Futures analogue of a "stop-limit" order.
- No real funds are used anywhere; all requests are sent to
  `https://testnet.binancefuture.com`.

## 7. Bonus implemented

- **Third order type**: STOP_LIMIT (`STOP` order on Binance Futures).
