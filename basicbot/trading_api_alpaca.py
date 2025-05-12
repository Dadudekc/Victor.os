import alpaca_trade_api as tradeapi

# ✅ Dynamic Import Handling (Supports module & standalone execution)
try:
    from basicbot.logger import setup_logging  
    from basicbot.config import config  
except ImportError:
    from logger import setup_logging  
    from config import config  

class TradingAPI:
    """
    A wrapper for the Alpaca API.
    Uses API credentials from config.py for authentication and trading.
    """

    def __init__(self):
        """Initialize the Alpaca API client and logger."""
        # ✅ Setup logger early in __init__
        self.logger = setup_logging("trading_api_alpaca")
        
        # ✅ Check API credentials
        if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
            self.logger.error("🚨 Missing Alpaca API credentials! Check your `.env` file.")
            raise ValueError("❌ Alpaca API credentials not found!")

        # ✅ Initialize the API connection
        try:
            self.api = tradeapi.REST(
                config.ALPACA_API_KEY, 
                config.ALPACA_SECRET_KEY, 
                config.ALPACA_BASE_URL, 
                api_version="v2"
            )
            self.logged_in = True
            self.logger.info("✅ Alpaca TradingAPI initialized successfully.")
        except Exception as e:
            self.logger.error(f"❌ Alpaca API Initialization Failed: {e}")
            self.logged_in = False
            raise

    def place_order(self, symbol: str, qty: int, side: str) -> dict:
        """
        Place a market order using Alpaca's API.

        :param symbol: Stock ticker (e.g., "TSLA")
        :param qty: Number of shares to buy/sell
        :param side: "buy" or "sell"
        :return: Dictionary with order ID and status, or None if failed.
        """
        if not self.logged_in:
            self.logger.error("🚫 Cannot place order. TradingAPI is logged out!")
            return None

        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type="market",
                time_in_force="gtc"
            )
            self.logger.info(f"✅ Order Executed: {side.upper()} {qty} shares of {symbol}")
            return {"id": order.id, "state": order.status}
        except Exception as e:
            self.logger.error(f"❌ Order Failed: {e}")
            return None

    def get_account(self) -> dict:
        """
        Retrieve account details including buying power and equity.

        :return: Dictionary with "buying_power" and "equity", or None if failed.
        """
        if not self.logged_in:
            self.logger.error("🚫 Cannot fetch account details. TradingAPI is logged out!")
            return None

        try:
            account = self.api.get_account()
            return {"buying_power": account.buying_power, "equity": account.equity}
        except Exception as e:
            self.logger.error(f"❌ Error fetching account details: {e}")
            return None

    def get_position(self, symbol: str = config.SYMBOL) -> tuple:
        """
        Fetch the current position for a given stock.

        :param symbol: Stock ticker (default: config.SYMBOL)
        :return: Tuple (quantity, cost_basis) or (0, 0) if no position found.
        """
        if not self.logged_in:
            self.logger.error("🚫 Cannot fetch position. TradingAPI is logged out!")
            return 0, 0

        try:
            position = self.api.get_position(symbol)
            return int(position.qty), float(position.cost_basis)
        except tradeapi.rest.APIError as e:
            self.logger.warning(f"⚠️ No position found for {symbol} ({e})")
            return 0, 0
        except Exception as e:
            self.logger.error(f"❌ Error fetching position: {e}")
            return 0, 0

    def logout(self):
        """Marks the API session as closed and prevents further calls."""
        self.logged_in = False
        self.logger.info("🛑 Logged out from Alpaca TradingAPI.")

# ✅ Run standalone for quick testing.
if __name__ == "__main__":
    try:
        api = TradingAPI()
        
        # ✅ Fetch account info
        account_info = api.get_account()
        api.logger.info(f"📊 Account Info: {account_info}")

        # ✅ Fetch a stock position
        symbol = "TSLA"
        qty, cost = api.get_position(symbol)
        api.logger.info(f"📈 Position in {symbol}: {qty} shares @ ${cost}")

        # ✅ Test order (CAUTION: Uncomment for live trading!)
        # api.place_order("TSLA", qty=1, side="buy")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if "api" in locals():
            api.logout()
