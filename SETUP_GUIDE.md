# Setup Guide

## Prerequisites

- Python 3.10 or higher
- Telegram account with a bot created
- (Optional) Binance account for API access

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/choch-alert-backend.git
cd choch-alert-backend
```

### 2. Create Virtual Environment

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Telegram Bot

#### Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the **bot token** (looks like: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

#### Get Your Chat ID

1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram
2. Start the bot
3. Copy your **chat ID** (a number like: `123456789`)

Alternatively, you can:
1. Start your bot (send `/start` to it)
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":...}` in the response

### 5. Configure Environment Variables

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` with your favorite editor:
```bash
nano .env  # or vim, code, notepad++, etc.
```

**Required settings:**
```ini
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**Optional settings:**
```ini
SYMBOL=BTCUSDT
TIMEFRAMES=5m,15m,30m,1h
PIVOT_LEFT=1
PIVOT_RIGHT=1
```

### 6. Test the Setup

Run tests to ensure everything is working:
```bash
pytest tests/ -v
```

### 7. Run the Application

**Manual start:**
```bash
python main.py
```

**Using helper scripts:**

Linux/Mac:
```bash
chmod +x run.sh
./run.sh
```

Windows:
```bash
run.bat
```

### 8. Access the Dashboard

Open your web browser and go to:
```
http://localhost:5000
```

You should see the CHoCH Alert Dashboard!

## Docker Setup (Alternative)

If you prefer using Docker:

### Build and Run

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Stop

```bash
docker-compose down
```

## Troubleshooting

### "Configuration error: TELEGRAM_BOT_TOKEN is required"
- Make sure you copied `.env.example` to `.env`
- Check that `TELEGRAM_BOT_TOKEN` is set correctly in `.env`

### "Telegram connection failed"
- Verify your bot token is correct
- Verify your chat ID is correct
- Make sure you've started the bot (sent `/start` to it)

### "WebSocket not supported, falling back to polling"
- This is normal if CCXT doesn't support WebSocket for the exchange
- The system will automatically use polling instead
- You can increase `UPDATE_INTERVAL` in `.env` if needed

### "Rate limit exceeded"
- Reduce the number of timeframes
- Increase `UPDATE_INTERVAL`
- Add Binance API credentials for higher rate limits

### Import Errors
- Make sure you're in the virtual environment
- Reinstall dependencies: `pip install -r requirements.txt`

## Advanced Configuration

### Using Binance API Keys

While not required for public data, API keys provide:
- Higher rate limits
- Access to account-specific data
- More reliable connections

Add to `.env`:
```ini
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret_key
```

### Customizing Pivot Detection

Adjust sensitivity by changing:
```ini
PIVOT_LEFT=2      # More conservative
PIVOT_RIGHT=2     # More conservative
```

### Variant Filters

Enable/disable specific pivot variants:
```ini
USE_VARIANT_FILTER=1
ALLOW_PH1=1
ALLOW_PH2=1
ALLOW_PH3=0  # Disable PH3
```

## Next Steps

- Monitor the logs for alerts
- Check the web dashboard for real-time updates
- Adjust configuration as needed
- Add more timeframes if desired
- Set up as a service for 24/7 operation

## Support

If you encounter issues:
1. Check the logs: `choch_alert.log`
2. Review this guide again
3. Check the [README.md](README.md)
4. Open an issue on GitHub

Happy trading! 📈
