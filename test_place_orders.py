"""
Test Order Placement với TP/SL logic mới
"""
import asyncio
import os
from dotenv import load_dotenv
import ccxt.async_support as ccxt
from datetime import datetime

load_dotenv()

async def test_order_placement():
    """Test đặt lệnh với TP/SL"""
    
    # Initialize exchange
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    # Enable demo trading
    exchange.enable_demo_trading(True)
    
    try:
        await exchange.load_markets()
        print("✓ Connected to Binance Futures Demo")
        
        # Set One-Way position mode
        try:
            await exchange.fapiPrivateGetPositionSideDual()
            print("✓ Already in One-Way position mode")
        except:
            await exchange.fapiPrivatePostPositionSideDual({'dualSidePosition': 'false'})
            print("✓ Switched to One-Way position mode")
        
        # Get current balance
        balance = await exchange.fetch_balance()
        usdt_balance = balance['USDT']['free']
        print(f"✓ Balance: {usdt_balance:.2f} USDT\n")
        
        # Test symbol
        symbol = 'BTC/USDT:USDT'
        leverage = 20
        position_size = 200  # $200 USDT
        
        # Set leverage
        await exchange.set_leverage(leverage, symbol)
        print(f"✓ Set leverage to {leverage}x for {symbol}")
        
        # Get current price
        ticker = await exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        print(f"Current BTC price: ${current_price:,.2f}\n")
        
        # ====== SIMULATE CHoCH SIGNAL - SHORT SETUP ======
        print("="*80)
        print("🎯 SIMULATING SHORT SIGNAL")
        print("="*80)
        
        # Giả định pivot points
        bar8_high = current_price * 1.02    # High8: +2% above current
        bar8_body_low = current_price * 1.015  # Body8: +1.5%
        bar5_body_low = current_price * 0.99   # Body5 (TP): -1%
        bar4_body_high = current_price * 1.03  # Body4 (SL): +3%
        
        entry1 = bar8_high      # Entry 1 = High8
        entry2 = bar8_body_low  # Entry 2 = Body8
        tp = bar5_body_low      # TP = Body5
        sl = bar4_body_high     # SL = Body4
        
        print(f"Entry 1 (High8): ${entry1:,.2f}")
        print(f"Entry 2 (Body8): ${entry2:,.2f}")
        print(f"TP (Body5): ${tp:,.2f}")
        print(f"SL (Body4): ${sl:,.2f}\n")
        
        # Check if price already passed TP
        if current_price <= tp:
            print("⚠️  Price already below TP, would skip this signal")
            return
        
        # Calculate quantity
        entry_size = position_size / 2  # $100 per entry
        worst_price = min(entry1, entry2)
        quantity = (entry_size * 1.02) / worst_price  # +2% buffer
        quantity = round(quantity, 3)  # Round to 3 decimals
        
        print(f"Quantity per entry: {quantity}")
        print(f"Notional Entry1: ${quantity * entry1:.2f}")
        print(f"Notional Entry2: ${quantity * entry2:.2f}")
        print(f"Total position: ${quantity * 2 * current_price:.2f}\n")
        
        # ====== PLACE ORDERS ======
        print("="*80)
        print("📋 PLACING ORDERS (ENTRY + TP/SL SEPARATELY)")
        print("="*80)
        
        # 1. Entry 1 - Limit order at High8
        print("\n1️⃣ Placing Entry1 (SELL limit @ High8)...")
        entry1_order = await exchange.create_order(
            symbol=symbol,
            type='limit',
            side='sell',
            amount=quantity,
            price=entry1,
            params={'newClientOrderId': f'ENTRY1_TEST_{int(datetime.now().timestamp()*1000)}'}
        )
        print(f"   ✅ Order ID: {entry1_order['id']}")
        print(f"   Entry Price: ${entry1:,.2f}, Qty: {quantity}")
        
        # 2. Entry 2 - Limit order at Body8
        print("\n2️⃣ Placing Entry2 (SELL limit @ Body8)...")
        entry2_order = await exchange.create_order(
            symbol=symbol,
            type='limit',
            side='sell',
            amount=quantity,
            price=entry2,
            params={'newClientOrderId': f'ENTRY2_TEST_{int(datetime.now().timestamp()*1000)}'}
        )
        print(f"   ✅ Order ID: {entry2_order['id']}")
        print(f"   Entry Price: ${entry2:,.2f}, Qty: {quantity}")
        
        # 3. Take Profit - TAKE_PROFIT_MARKET order
        print("\n3️⃣ Placing Take Profit (BUY @ Body5)...")
        tp_order = await exchange.create_order(
            symbol=symbol,
            type='TAKE_PROFIT_MARKET',
            side='buy',
            amount=quantity * 2,  # Total quantity for both entries
            params={
                'stopPrice': tp,
                'newClientOrderId': f'TP_TEST_{int(datetime.now().timestamp()*1000)}'
            }
        )
        print(f"   ✅ Order ID: {tp_order['id']}")
        print(f"   Trigger Price: ${tp:,.2f}, Qty: {quantity * 2}")
        
        # 4. Stop Loss - STOP_MARKET order
        print("\n4️⃣ Placing Stop Loss (BUY @ Body4)...")
        sl_order = await exchange.create_order(
            symbol=symbol,
            type='STOP_MARKET',
            side='buy',
            amount=quantity * 2,  # Total quantity for both entries
            params={
                'stopPrice': sl,
                'newClientOrderId': f'SL_TEST_{int(datetime.now().timestamp()*1000)}'
            }
        )
        print(f"   ✅ Order ID: {sl_order['id']}")
        print(f"   Trigger Price: ${sl:,.2f}, Qty: {quantity * 2}")
        
        print("\n" + "="*80)
        print("✅ ALL ORDERS PLACED SUCCESSFULLY!")
        print("="*80)
        
        # Fetch all open orders
        print("\n📊 Checking open orders...")
        open_orders = await exchange.fetch_open_orders(symbol)
        print(f"Total open orders: {len(open_orders)}")
        for order in open_orders:
            price_display = order.get('price') or order.get('stopPrice') or order.get('triggerPrice') or 0
            print(f"  - {order['type']:20} {order['side']:4} {order['amount']:8.3f} @ ${price_display:,.2f}")
        
        # Cancel all test orders
        print("\n🧹 Cleaning up test orders...")
        for order_id in [entry1_order['id'], entry2_order['id'], tp_order['id'], sl_order['id']]:
            try:
                await exchange.cancel_order(order_id, symbol)
                print(f"   ✓ Cancelled order {order_id}")
            except Exception as e:
                print(f"   ⚠️  Failed to cancel {order_id}: {e}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await exchange.close()

if __name__ == '__main__':
    asyncio.run(test_order_placement())
