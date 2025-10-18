# 🎯 CHoCH Alert Backend - Complete Repository

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)

**Backend Python system để phát hiện tín hiệu CHoCH (Change of Character) từ logic Pine Script, sử dụng CCXT cho dữ liệu Binance và gửi cảnh báo qua Telegram.**

---

## ✨ Highlights

- 🎯 **Accurate CHoCH Detection** - Replicated Pine Script logic với độ chính xác cao
- 📊 **Multi-Timeframe** - Theo dõi đồng thời nhiều khung thời gian (5m, 15m, 30m, 1h, ...)
- ⚡ **Async Architecture** - Hiệu suất cao với asyncio và CCXT async
- 📱 **Telegram Alerts** - Thông báo tức thời với format đẹp mắt
- 🌐 **Real-time Dashboard** - Web interface với SocketIO
- 🐳 **Docker Ready** - Deploy dễ dàng với Docker/Docker Compose
- ✅ **Well Tested** - Unit tests với pytest
- 📚 **Comprehensive Docs** - Documentation đầy đủ cho mọi thành phần

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Documentation](#-documentation)
- [Architecture](#-architecture)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Telegram Bot (get token from [@BotFather](https://t.me/BotFather))
- Your Telegram Chat ID (get from [@userinfobot](https://t.me/userinfobot))

### 1-Minute Setup

```bash
# Clone repository
git clone https://github.com/yourusername/choch-alert-backend.git
cd choch-alert-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Telegram credentials

# Run
python main.py

# Access dashboard
# Open http://localhost:5000 in browser
```

**That's it! 🎉**

---

## 🌟 Features

### Core Functionality
- ✅ **Pivot Detection** - Phát hiện Pivot High/Low với left/right bars
- ✅ **Variant Classification** - 6 loại variants (PH1/2/3, PL1/2/3)
- ✅ **6-Pattern Analysis** - Kiểm tra cấu trúc 6-pivot với constraints đầy đủ
- ✅ **CHoCH Signals** - Phát hiện Change of Character chính xác
- ✅ **Fake Pivot Insertion** - Xử lý consecutive same-type pivots

### Multi-Timeframe
- ✅ **Concurrent Monitoring** - Theo dõi nhiều TF cùng lúc
- ✅ **Independent States** - Mỗi TF có state riêng
- ✅ **Configurable** - Chọn TF tùy ý qua config

### Data & Alerts
- ✅ **CCXT Integration** - Binance data với WebSocket/Polling
- ✅ **Telegram Notifications** - Format đẹp với Markdown
- ✅ **TradingView Links** - Direct links đến charts
- ✅ **Historical Data** - Load 500 bars on startup

### Web Interface
- ✅ **Real-time Dashboard** - SocketIO cho updates tức thời
- ✅ **Alert History** - Lưu 100 alerts gần nhất
- ✅ **Browser Notifications** - Native notifications
- ✅ **Beautiful UI** - Bootstrap 5 responsive design

### Developer Experience
- ✅ **Clean Code** - Type hints, docstrings, PEP 8
- ✅ **Well Tested** - Pytest với fixtures
- ✅ **Comprehensive Docs** - API docs, setup guide, architecture
- ✅ **Easy Deployment** - Docker, scripts, systemd

---

## 📥 Installation

### Method 1: Manual Setup

```bash
# 1. Clone
git clone https://github.com/yourusername/choch-alert-backend.git
cd choch-alert-backend

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
nano .env  # Edit with your credentials
```

### Method 2: Using Helper Scripts

**Linux/Mac:**
```bash
chmod +x run.sh
./run.sh
```

**Windows:**
```bash
run.bat
```

### Method 3: Docker

```bash
# With Docker Compose
docker-compose up -d

# Or build manually
docker build -t choch-alert .
docker run -p 5000:5000 --env-file .env choch-alert
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```ini
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Trading (Optional)
SYMBOL=BTCUSDT
TIMEFRAMES=5m,15m,30m,1h

# Pivot Settings (Optional)
PIVOT_LEFT=1
PIVOT_RIGHT=1
KEEP_PIVOTS=200

# Variant Filters (Optional - 1=enabled, 0=disabled)
USE_VARIANT_FILTER=1
ALLOW_PH1=1
ALLOW_PH2=1
ALLOW_PH3=1
ALLOW_PL1=1
ALLOW_PL2=1
ALLOW_PL3=1

# Binance API (Optional - for higher rate limits)
BINANCE_API_KEY=
BINANCE_SECRET=

# Flask (Optional)
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### Detailed Configuration Guide

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for step-by-step instructions.

---

## 💻 Usage

### Basic Usage

```bash
python main.py
```

Output:
```
🚀 Initializing CHoCH Alert System...
✅ System initialized
================================================================================
CHoCH ALERT SYSTEM
================================================================================
Symbol: BTCUSDT
Timeframes: 5m, 15m, 30m, 1h
Pivot Settings: Left=1, Right=1
Variant Filter: True
================================================================================
✅ Telegram bot connected: YourBotName
🌐 Starting Flask web server on 0.0.0.0:5000
🌐 Web dashboard available at http://0.0.0.0:5000
✅ All watchers started successfully
🔍 Monitoring for CHoCH signals...
Press Ctrl+C to stop
```

### Access Web Dashboard

Open browser: `http://localhost:5000`

You'll see:
- Real-time alert table
- Connection status
- Alert count
- TradingView links

### Telegram Alerts

When CHoCH detected, you'll receive:

```
🚨 CHoCH SIGNAL DETECTED 🚨

⏰ Time: 2025-10-18 14:30:00
💰 Mã: BTCUSDT
📊 Khung: 5m
📈 Hướng: Long
🎯 Loại: CHoCH Up
💵 Price: $67,432.50

🔗 View on TradingView
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Main documentation (this file) |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Detailed setup instructions |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | API reference for all modules |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture diagrams |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | Complete project summary |

### Quick Links

- **Getting Started**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **API Reference**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Troubleshooting**: [README.md#troubleshooting](#-troubleshooting)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CHoCH Alert System                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
  ┌──────────┐      ┌──────────────┐     ┌──────────┐
  │ Binance  │      │   Detector   │     │   Web    │
  │  CCXT    │──┬──>│   CHoCH      │──┬─>│ SocketIO │
  │  Async   │  │   │  Logic       │  │  │ + Flask  │
  └──────────┘  │   └──────────────┘  │  └──────────┘
                │                     │
                │                     └──> Telegram
                │                           Alerts
                └──> Multi-Timeframe
                     State Management
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams.

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_detector.py::TestChochDetector::test_detect_pivots -v
```

### With Coverage

```bash
pytest tests/ --cov=detectors --cov=data --cov=alert --cov-report=html
```

### Test Structure

```
tests/
├── __init__.py
└── test_detector.py
    ├── Fixtures (sample data)
    ├── TestChochDetector (main tests)
    └── TestTimeframeState (state tests)
```

---

## 🐳 Deployment

### Docker Compose (Recommended)

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Systemd Service (Linux)

Create `/etc/systemd/system/choch-alert.service`:

```ini
[Unit]
Description=CHoCH Alert Backend
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/choch-alert-backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable choch-alert
sudo systemctl start choch-alert
sudo systemctl status choch-alert
```

### Production Checklist

- [ ] Use strong Flask secret key
- [ ] Enable HTTPS (nginx/caddy)
- [ ] Set up log rotation
- [ ] Monitor resource usage
- [ ] Set up alerts for system errors
- [ ] Backup configuration
- [ ] Document your setup

---

## 🔧 Troubleshooting

### Configuration Errors

**Problem:** "Configuration error: TELEGRAM_BOT_TOKEN is required"

**Solution:**
```bash
# Make sure .env exists
cp .env.example .env

# Edit .env
nano .env
# Add your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

### Telegram Not Working

**Problem:** Alerts not arriving in Telegram

**Solutions:**
1. Verify bot token is correct
2. Verify chat ID is a number
3. Start the bot (send `/start` to it first)
4. Check logs for errors: `tail -f choch_alert.log`

### WebSocket Fallback

**Problem:** "WebSocket not supported, falling back to polling"

**Solution:** This is normal! The system automatically uses polling. You can:
- Increase `UPDATE_INTERVAL` in `.env` to reduce API calls
- Add Binance API credentials for higher rate limits

### High CPU Usage

**Solutions:**
- Reduce number of timeframes
- Increase `UPDATE_INTERVAL`
- Use WebSocket instead of polling (add API keys)

### Import Errors

**Problem:** `ModuleNotFoundError`

**Solution:**
```bash
# Make sure you're in virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Start for Contributors

```bash
# Fork the repo
# Clone your fork
git clone https://github.com/yourusername/choch-alert-backend.git

# Create branch
git checkout -b feature/amazing-feature

# Make changes
# Write tests
# Run tests
pytest tests/ -v

# Commit
git commit -m "Add amazing feature"

# Push
git push origin feature/amazing-feature

# Create Pull Request
```

---

## 📊 Project Stats

- **Lines of Code**: ~3,500+
- **Files**: 25+
- **Tests**: 15+ test cases
- **Documentation**: 7 comprehensive docs
- **Dependencies**: 12 packages
- **Supported Python**: 3.10+

---

## 🙏 Acknowledgments

- Pine Script community for original indicator logic
- CCXT library for crypto exchange integration
- Flask & SocketIO for real-time web capabilities
- Telegram for bot API

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

- **Documentation**: Check docs in repo
- **Issues**: [GitHub Issues](https://github.com/yourusername/choch-alert-backend/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/choch-alert-backend/discussions)

---

## ⚠️ Disclaimer

**Chỉ sử dụng cho mục đích giáo dục và nghiên cứu.**

This software is for educational and research purposes only. Trading cryptocurrencies carries risk. Always do your own research and never invest more than you can afford to lose. The authors are not responsible for any financial losses.

---

## 🎯 Roadmap

- [x] Multi-timeframe CHoCH detection
- [x] CCXT integration
- [x] Telegram alerts
- [x] Web dashboard
- [x] Docker support
- [x] Comprehensive documentation
- [ ] Backtesting mode
- [ ] Multiple exchanges
- [ ] Database persistence
- [ ] Discord notifications
- [ ] Mobile app
- [ ] Performance analytics

---

## 📈 Example Output

### Terminal
```
[5m] New bar: 2025-10-18 14:30:00 | Close: 67432.50
🎯 CHoCH detected on 5m: CHoCH Up
✅ Alert sent to Telegram: CHoCH Up on 5m
📡 Broadcasted alert: CHoCH Up on 5m
```

### Web Dashboard
![Dashboard Preview](https://via.placeholder.com/800x400?text=Real-time+CHoCH+Dashboard)

### Telegram
![Telegram Alert](https://via.placeholder.com/400x300?text=Telegram+Alert+Preview)

---

<div align="center">

**Made with ❤️ for the trading community**

⭐ Star this repo if you find it useful!

[Report Bug](https://github.com/yourusername/choch-alert-backend/issues) · [Request Feature](https://github.com/yourusername/choch-alert-backend/issues) · [Documentation](SETUP_GUIDE.md)

</div>
