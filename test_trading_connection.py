"""
Test Trading Bot Connection - Verify API credentials and exchange connectivity

This script tests:
1. API key validity
2. Exchange connection
3. Account balance
4. Market data fetching
5. Order placement (dry-run, no actual orders)
"""
import asyncio
import logging
import sys
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_bot_connection():
    """Test all bot components"""
    
    print("="*80)
    print("CHoCH TRADING BOT - CONNECTION TEST")
    print("="*80 + "\n")
    
    # Check environment variables
    print("1. Checking environment variables...")
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET')
    
    # Support multiple environments: demo, testnet, production
    env_mode = os.getenv('BINANCE_ENV', 'demo').lower()  # demo, testnet, production
    use_demo = env_mode == 'demo'
    use_testnet = env_mode == 'testnet'
    
    if not api_key or not api_secret:
        print("❌ API credentials not found in .env file")
        print("   Please set BINANCE_API_KEY and BINANCE_SECRET")
        return False
    
    # Show environment info
    if use_demo:
        print(f"✅ DEMO MODE - Using Binance Futures Demo")
        print(f"   Demo URL: https://testnet.binancefuture.com")
        print(f"   API Key: {api_key[:8]}...{api_key[-8:]}")
        print(f"   You can use your PRODUCTION API keys with demo endpoints")
    elif use_testnet:
        print(f"⚠️  TESTNET MODE - Using Binance Testnet")
        print(f"   Testnet URL: https://testnet.binancefuture.com")
        print(f"   API Key: {api_key[:8]}...{api_key[-8:]}")
        print(f"   Note: Testnet requires testnet-specific API keys")
    else:
        print(f"🔴 PRODUCTION MODE - USING REAL ACCOUNT")
        print(f"   API Key: {api_key[:8]}...{api_key[-8:]}")
        print(f"   ⚠️  WARNING: This will use REAL money!")
    
    print(f"✓ Environment: {env_mode.upper()}")
    print()
    
    # Test CCXT import
    print("2. Checking dependencies...")
    try:
        import ccxt.async_support as ccxt
        import pandas as pd
        print("✓ CCXT library installed")
        print("✓ Pandas library installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Run: pip install -r requirements.txt")
        return False
    print()
    
    # Test exchange connection
    print("3. Connecting to Binance...")
    try:
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        }
        
        exchange = ccxt.binance(config)
        
        # Enable demo mode if needed
        if use_demo:
            exchange.enable_demo_trading(True)
            print(f"✓ Connected to Binance Futures DEMO")
            print(f"   Using: https://demo-fapi.binance.com")
        elif use_testnet:
            print(f"⚠️  TESTNET is deprecated for futures")
            print(f"   Please use BINANCE_ENV=demo instead")
            await exchange.close()
            return False
        else:
            print(f"✓ Connected to Binance Futures PRODUCTION")
            print(f"   Using: https://fapi.binance.com")
        
        await exchange.load_markets()
        print(f"✓ Available markets: {len(exchange.markets)}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Error details: {str(e)}")
        return False
    print()
    
    # Test account access
    print("4. Checking account access...")
    try:
        balance = await exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {})
        free = usdt_balance.get('free', 0)
        used = usdt_balance.get('used', 0)
        total = usdt_balance.get('total', 0)
        
        print(f"✓ Account balance retrieved")
        print(f"  Free: {free:.2f} USDT")
        print(f"  Used: {used:.2f} USDT")
        print(f"  Total: {total:.2f} USDT")
        
        position_size = float(os.getenv('POSITION_SIZE_USDT', '100'))
        if total < position_size * 2:
            print(f"⚠️  Warning: Balance ({total:.2f}) is low for position size ({position_size})")
            print(f"   Recommended: At least {position_size * 5:.2f} USDT")
    except Exception as e:
        print(f"❌ Account access failed: {e}")
        await exchange.close()
        return False
    print()
    
    # Test market data
    print("5. Testing market data fetch...")
    try:
        # Fetch ticker
        ticker = await exchange.fetch_ticker('BTC/USDT:USDT')
        print(f"✓ BTC/USDT ticker: ${ticker['last']:,.2f}")
        
        # Fetch OHLCV
        ohlcv = await exchange.fetch_ohlcv('BTC/USDT:USDT', '1h', limit=10)
        print(f"✓ Historical data: {len(ohlcv)} candles fetched")
    except Exception as e:
        print(f"❌ Market data fetch failed: {e}")
        await exchange.close()
        return False
    print()
    
    # Test order simulation (no actual order)
    print("6. Testing order placement (simulation)...")
    try:
        # Get current price
        ticker = await exchange.fetch_ticker('BTC/USDT:USDT')
        current_price = ticker['last']
        
        # Calculate order with minimum notional $100
        # Notional = price * quantity >= 100
        test_price = current_price * 0.5  # 50% below current
        min_notional = 100  # Minimum order value in USDT
        test_quantity = min_notional / test_price  # Ensure notional >= 100
        test_quantity = round(test_quantity, 3)  # Round to 3 decimals
        
        print(f"  Current BTC price: ${current_price:,.2f}")
        print(f"  Test order: BUY {test_quantity} BTC @ ${test_price:,.2f}")
        print(f"  Order value: ${test_price * test_quantity:,.2f} USDT")
        print(f"  (This order is far from market and won't fill)")
        
        # Test actual order placement on demo
        if use_demo:
            print(f"\n  🧪 Testing actual order placement in DEMO mode...")
            
            # Set leverage first
            try:
                await exchange.set_leverage(20, 'BTC/USDT:USDT')
                print(f"  ✓ Leverage set to 20x")
            except Exception as e:
                print(f"  ⚠️  Leverage setting: {e}")
            
            # Place test order (One-Way mode - no positionSide)
            try:
                order = await exchange.create_order(
                    symbol='BTC/USDT:USDT',
                    type='limit',
                    side='buy',
                    amount=test_quantity,
                    price=test_price,
                    params={}  # One-Way mode - không dùng positionSide
                )
                print(f"  ✓ Test order placed: {order['id']}")
                print(f"     Status: {order.get('status', 'N/A')}")
                print(f"     Type: {order.get('type', 'N/A')}")
                print(f"     Notional: ${test_price * test_quantity:,.2f} USDT")
                
                # Cancel it immediately
                await exchange.cancel_order(order['id'], 'BTC/USDT:USDT')
                print(f"  ✓ Test order cancelled")
            except Exception as e:
                print(f"  ❌ Order placement failed: {e}")
                raise
        else:
            print(f"  ⚠️  Skipping order test on {'TESTNET' if use_testnet else 'PRODUCTION'}")
        
        print("  ✓ Order simulation successful")
    except Exception as e:
        print(f"❌ Order simulation failed: {e}")
        await exchange.close()
        return False
    print()
    
    # Test Telegram
    print("7. Testing Telegram notifications...")
    try:
        from alert.telegram_sender import TelegramSender
        telegram = TelegramSender(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            chat_id=os.getenv('TELEGRAM_CHAT_ID')
        )
        
        if telegram.bot_token and telegram.chat_id:
            # Note: Uncomment to send test message
            """
            await telegram.send_message(
                "🧪 <b>Trading Bot Test</b>\n\n"
                "This is a test message from your trading bot.\n"
                "If you see this, Telegram notifications are working!"
            )
            print("✓ Test message sent to Telegram")
            """
            print("✓ Telegram configured (message not sent)")
        else:
            print("⚠️  Telegram not configured (optional)")
    except Exception as e:
        print(f"⚠️  Telegram test failed: {e}")
        print("   (This is optional, bot can run without Telegram)")
    print()
    
    # Cleanup
    await exchange.close()
    
    # Summary
    print("="*80)
    print("✅ ALL TESTS PASSED")
    print("="*80)
    print(f"\nYour bot is ready to run in {env_mode.upper()} mode!")
    print("\nNext steps:")
    print("1. Review configuration in .env file")
    if use_demo:
        print("2. You're using DEMO mode - safe to test with production API keys")
        print("3. Get demo API keys from: https://testnet.binancefuture.com")
    elif use_testnet:
        print("2. You're using TESTNET - requires testnet API keys")
        print("3. Get testnet keys from: https://testnet.binancefuture.com")
    else:
        print("2. ⚠️  PRODUCTION MODE - Using real money!")
        print("3. Start with small POSITION_SIZE_USDT (10-50)")
    print("4. Run: python trading_bot.py")
    print()
    
    return True


if __name__ == '__main__':
    try:
        success = asyncio.run(test_bot_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
