# Dual Exchange Setup - Architecture Documentation

## Overview

Hệ thống sử dụng **2 instance exchange riêng biệt** để tách biệt việc phân tích thị trường và thực thi lệnh.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CHoCH Alert System                       │
│                          (main.py)                           │
└───────────────────┬─────────────────┬───────────────────────┘
                    │                 │
        ┌───────────▼──────────┐     │
        │  Exchange Instance 1  │     │
        │  REALTIME DATA       │     │
        │  (BinanceFetcher)    │     │
        └──────────────────────┘     │
        • Purpose: Market Data        │
        • Source: Production          │
        • Used for: CHoCH Detection   │
                                      │
                        ┌─────────────▼──────────────┐
                        │  Exchange Instance 2       │
                        │  DEMO/LIVE TRADING         │
                        │  (BinanceFuturesAdapter)   │
                        └────────────────────────────┘
                        • Purpose: Order Execution
                        • Source: Testnet or Production
                        • Used for: Position Management
```

## Why Two Separate Instances?

### Problem
Trước đây chỉ dùng 1 instance exchange:
- Nếu dùng testnet → Orders an toàn nhưng market data không chính xác
- Nếu dùng production → Market data chính xác nhưng orders rủi ro

### Solution
Tách thành 2 instances độc lập:

#### 1. REALTIME DATA FETCHER (BinanceFetcher)
- **Purpose**: Fetch market data (OHLCV, prices, volume)
- **Source**: **ALWAYS** production/realtime
- **Why**: CHoCH signals need real market movements to be accurate
- **Note**: Even in demo trading mode, we analyze real market data

#### 2. DEMO/LIVE EXCHANGE (BinanceFuturesAdapter)
- **Purpose**: Execute orders & manage positions
- **Source**: Testnet (demo) **OR** Production (live) based on config
- **Why**: Practice strategies without risking real money
- **Note**: Uses demo funds but analyzes real market

## Configuration

### Environment Variables

```bash
# ==========================================
# API Keys - Separate for Each Exchange
# ==========================================

# Production API (for market data)
BINANCE_API_KEY=your_production_key
BINANCE_SECRET=your_production_secret

# Demo/Testnet API (for trading)
# Get from: https://testnet.binancefuture.com
BINANCE_API_KEY_DEMO=your_testnet_key
BINANCE_SECRET_DEMO=your_testnet_secret
# If not set, will fallback to BINANCE_API_KEY

# ==========================================
# Exchange Configuration
# ==========================================

# Market Data Configuration
USE_REALTIME_DATA=1  # 1=production data (default), 0=testnet data
                     # Typically always 1 even in demo mode

# Trading Configuration  
ENABLE_TRADING=1     # 1=enable trading, 0=simulation only
DEMO_TRADING=1       # 1=testnet orders, 0=production orders
POSITION_SIZE=100    # Position size in USDT
LEVERAGE=20          # Leverage multiplier
```

### Scenarios

#### Scenario 1: Safe Demo Trading (Recommended)
```bash
USE_REALTIME_DATA=1  # Use real market data
ENABLE_TRADING=1     # Enable trading
DEMO_TRADING=1       # Use testnet for orders
```
→ Analyze real market → Execute on testnet (safe) ✅

#### Scenario 2: Live Trading (Risky)
```bash
USE_REALTIME_DATA=1  # Use real market data
ENABLE_TRADING=1     # Enable trading
DEMO_TRADING=0       # Use production for orders
```
→ Analyze real market → Execute on production (risky) ⚠️

#### Scenario 3: Simulation Only
```bash
USE_REALTIME_DATA=1  # Use real market data
ENABLE_TRADING=0     # Disable trading
```
→ Analyze real market → No orders (safe) ✅

#### Scenario 4: Full Testnet (for testing)
```bash
USE_REALTIME_DATA=0  # Use testnet data
ENABLE_TRADING=1     # Enable trading
DEMO_TRADING=1       # Use testnet for orders
```
→ Analyze testnet data → Execute on testnet (for testing) 🧪

## Code Implementation

### main.py

```python
# 1. Initialize REALTIME data fetcher (uses production keys)
base_fetcher = BinanceFetcher(
    api_key=config.BINANCE_API_KEY,      # Production keys
    secret=config.BINANCE_SECRET,        # Production keys
    use_realtime=config.USE_REALTIME_DATA  # Default: True
)
self.fetcher = TimeframeAdapter(base_fetcher)

# 2. Initialize DEMO/LIVE trading exchange (uses demo keys)
self.demo_exchange = BinanceFuturesAdapter(
    api_key=config.BINANCE_API_KEY_DEMO,  # Demo/testnet keys
    secret=config.BINANCE_SECRET_DEMO,    # Demo/testnet keys
    demo_mode=config.DEMO_TRADING  # True=testnet, False=production
)

# 3. Position manager uses demo_exchange
position_manager = PositionManager(
    exchange=self.demo_exchange,
    enable_trading=True
)
```

### config.py

```python
# Production API (for market data)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET', '')

# Demo/Testnet API (for trading)
# Fallback to production keys if not set
BINANCE_API_KEY_DEMO = os.getenv('BINANCE_API_KEY_DEMO', 
                                  os.getenv('BINANCE_API_KEY', ''))
BINANCE_SECRET_DEMO = os.getenv('BINANCE_SECRET_DEMO', 
                                 os.getenv('BINANCE_SECRET', ''))
```

### BinanceFetcher

```python
class BinanceFetcher:
    def __init__(self, api_key: str = '', secret: str = '', use_realtime: bool = True):
        self.use_realtime = use_realtime
    
    async def initialize(self):
        self.exchange = ccxt.binance(config)
        
        if not self.use_realtime:
            # Only enable testnet if explicitly requested
            self.exchange.enable_demo_trading(True)
            logger.info("🧪 Data Fetcher: TESTNET mode")
        else:
            logger.info("📊 Data Fetcher: REALTIME mode")
```

### BinanceFuturesAdapter

```python
class BinanceFuturesAdapter:
    def __init__(self, api_key: str, secret: str, demo_mode: bool = True):
        self.demo_mode = demo_mode
    
    async def initialize(self):
        self.exchange = ccxt.binanceusdm({...})
        
        if self.demo_mode:
            self.exchange.enable_demo_trading(True)
            logger.info("🧪 Trading Exchange: TESTNET")
        else:
            logger.warning("⚠️ Trading Exchange: LIVE (real money!)")
```

## Benefits

1. **Safety**: Test strategies with real market data without risk
2. **Accuracy**: CHoCH signals based on real market movements
3. **Flexibility**: Can switch between demo/live without changing data source
4. **Clear Separation**: Market analysis ≠ Order execution

## Logs Example

```
[*] Initializing CHoCH Alert System...
==========================================
DUAL EXCHANGE SETUP
==========================================
📊 Instance 1: REALTIME DATA FETCHER
   Purpose: Fetch market data (OHLCV, prices)
   Source: ALWAYS production (realtime prices)
   Reason: CHoCH signals need real market data

🎮 Instance 2: DEMO/LIVE EXCHANGE
   Purpose: Execute orders & manage positions
   Source: TESTNET (demo)
   Reason: Test strategies without real money risk
==========================================

✓ Market Data Fetcher: REALTIME (for CHoCH detection)
✓ Trading Exchange: TESTNET (position management)
✓ Position Manager: $100 @ 20x leverage
✓ Trading Bot: ACTIVE
```

## Best Practices

1. **Always use realtime data** for signal detection (USE_REALTIME_DATA=1)
2. **Start with demo mode** to test strategies (DEMO_TRADING=1)
3. **Only switch to live** after extensive testing (DEMO_TRADING=0)
4. **Monitor both instances** separately in logs
5. **Keep position size small** when first going live

## Testing Checklist

- [ ] Verify realtime data fetcher connects to production
- [ ] Verify trading exchange connects to testnet (demo mode)
- [ ] Test CHoCH signal detection with real data
- [ ] Test order execution on testnet
- [ ] Monitor position management on testnet
- [ ] Verify logs show correct instances
- [ ] Test graceful shutdown of both instances

## Troubleshooting

### Issue: No market data
- Check `USE_REALTIME_DATA=1`
- Check API keys are valid
- Check production API is accessible

### Issue: Orders not executing
- Check `ENABLE_TRADING=1`
- Check `DEMO_TRADING` setting
- Check testnet/production API keys
- Check exchange initialization logs

### Issue: Using wrong data source
- Check logs for "REALTIME" vs "TESTNET"
- Verify config.USE_REALTIME_DATA value
- Restart system after config changes

## Future Enhancements

- [ ] Add health check for both instances
- [ ] Add metrics for data vs trading latency
- [ ] Add automatic fallback if realtime fails
- [ ] Add UI to monitor both exchanges separately
