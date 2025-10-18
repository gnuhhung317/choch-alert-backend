# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-18

### Added
- Initial release
- Multi-timeframe CHoCH detection based on Pine Script logic
- Async CCXT integration for Binance data fetching
- Telegram alert notifications
- Real-time web dashboard with SocketIO
- Pivot detection with variant classification (PH1/2/3, PL1/2/3)
- 6-pattern analysis for CHoCH confirmation
- Configurable filters and settings via environment variables
- Unit tests for detector module
- Docker support
- Comprehensive documentation

### Features
- **Multi-Timeframe Support**: Monitor 5m, 15m, 30m, 1h simultaneously
- **Real-time Alerts**: Telegram notifications and web dashboard
- **Accurate Detection**: Replicated Pine Script logic with high fidelity
- **Async Architecture**: Efficient concurrent data fetching
- **Web Interface**: Beautiful real-time dashboard with SocketIO
- **Configurable**: All parameters via .env file
- **Tested**: Unit tests with pytest
- **Docker Ready**: Easy deployment with Docker/Docker Compose

[1.0.0]: https://github.com/yourusername/choch-alert-backend/releases/tag/v1.0.0
