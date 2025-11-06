"""
Check open orders on Demo account
"""
import asyncio
import ccxt.async_support as ccxt
from dotenv import load_dotenv
import os

load_dotenv()

async def check_orders():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET')
    
    config = {
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    }
    
    exchange = ccxt.binance(config)
    exchange.enable_demo_trading(True)
    
    await exchange.load_markets()
    
    print("="*80)
    print("CHECKING DEMO ACCOUNT STATUS")
    print("="*80)
    
    # Check balance
    print("\n1. Balance:")
    balance = await exchange.fetch_balance()
    usdt = balance.get('USDT', {})
    print(f"   Free: {usdt.get('free', 0):.2f} USDT")
    print(f"   Used: {usdt.get('used', 0):.2f} USDT")
    print(f"   Total: {usdt.get('total', 0):.2f} USDT")
    
    # Check open orders
    print("\n2. Open Orders:")
    try:
        orders = await exchange.fetch_open_orders('BTC/USDT:USDT')
        if orders:
            for order in orders:
                print(f"   Order ID: {order['id']}")
                print(f"   Side: {order['side']}")
                print(f"   Price: {order['price']}")
                print(f"   Amount: {order['amount']}")
                print(f"   Status: {order['status']}")
                print()
        else:
            print("   No open orders")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check positions
    print("\n3. Positions:")
    try:
        positions = await exchange.fetch_positions(['BTC/USDT:USDT'])
        if positions:
            for pos in positions:
                if float(pos.get('contracts', 0)) != 0:
                    print(f"   Symbol: {pos['symbol']}")
                    print(f"   Side: {pos['side']}")
                    print(f"   Size: {pos['contracts']}")
                    print(f"   Entry Price: {pos.get('entryPrice', 'N/A')}")
                    print(f"   Unrealized PnL: {pos.get('unrealizedPnl', 'N/A')}")
                    print()
        if not any(float(p.get('contracts', 0)) != 0 for p in positions):
            print("   No open positions")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Recent trades
    print("\n4. Recent Trades (last 10):")
    try:
        trades = await exchange.fetch_my_trades('BTC/USDT:USDT', limit=10)
        if trades:
            for trade in trades[-5:]:  # Show last 5
                print(f"   Time: {trade['datetime']}")
                print(f"   Side: {trade['side']}")
                print(f"   Price: {trade['price']}")
                print(f"   Amount: {trade['amount']}")
                print()
        else:
            print("   No recent trades")
    except Exception as e:
        print(f"   Error: {e}")
    
    await exchange.close()
    print("="*80)

if __name__ == '__main__':
    asyncio.run(check_orders())
