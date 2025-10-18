"""
Telegram Alert Sender - Send formatted CHoCH alerts via Telegram Bot API
"""
import requests
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramSender:
    """Send alerts to Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram sender
        
        Args:
            bot_token: Telegram Bot API token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    def format_message(self, alert_data: Dict) -> str:
        """
        Format alert data into readable message
        
        Args:
            alert_data: Dict with keys: time_date, mã, khung, hướng, loại, link, price
        
        Returns:
            Formatted message string
        """
        # Format price with appropriate decimals
        price = alert_data.get('price', 0)
        price_str = f"{price:,.2f}" if price else "N/A"
        
        message = (
            f"🚨 *CHoCH SIGNAL DETECTED* 🚨\n\n"
            f"⏰ *Time:* {alert_data.get('time_date', 'N/A')}\n"
            f"💰 *Mã:* {alert_data.get('mã', 'N/A')}\n"
            f"📊 *Khung:* {alert_data.get('khung', 'N/A')}\n"
            f"📈 *Hướng:* {alert_data.get('hướng', 'N/A')}\n"
            f"🎯 *Loại:* {alert_data.get('loại', 'N/A')}\n"
            f"💵 *Price:* ${price_str}\n\n"
            f"🔗 [View on TradingView]({alert_data.get('link', '#')})"
        )
        
        return message
    
    def send_alert(self, alert_data: Dict) -> bool:
        """
        Send alert to Telegram
        
        Args:
            alert_data: Alert data dictionary
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = self.format_message(alert_data)
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Alert sent to Telegram: {alert_data.get('loại')} on {alert_data.get('khung')}")
                return True
            else:
                logger.error(f"❌ Failed to send Telegram alert: {response.status_code} - {response.text}")
                return False
        
        except requests.RequestException as e:
            logger.error(f"❌ Telegram API request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending Telegram alert: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test Telegram bot connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.api_url}/getMe",
                timeout=5
            )
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_name = bot_info['result'].get('first_name', 'Unknown')
                    logger.info(f"✅ Telegram bot connected: {bot_name}")
                    return True
            
            logger.error(f"❌ Telegram bot connection failed: {response.text}")
            return False
        
        except Exception as e:
            logger.error(f"❌ Telegram connection test failed: {e}")
            return False


def create_alert_data(symbol: str, timeframe: str, signal_type: str, 
                     direction: str, price: float, timestamp: datetime) -> Dict:
    """
    Create alert data dictionary
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Timeframe (e.g., '5m')
        signal_type: Signal type (e.g., 'CHoCH Up')
        direction: Direction ('Long' or 'Short')
        price: Current price
        timestamp: Signal timestamp
    
    Returns:
        Alert data dictionary
    """
    # Convert timeframe to TradingView format
    tv_interval = convert_tf_to_tradingview(timeframe)
    
    # Format symbol for TradingView (BTC/USDT -> BTCUSDT)
    tv_symbol = symbol.replace('/', '')
    
    # Create TradingView link
    link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{tv_symbol}&interval={tv_interval}"
    
    return {
        'time_date': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'mã': tv_symbol,
        'khung': timeframe,
        'hướng': direction,
        'loại': signal_type,
        'price': price,
        'link': link
    }


def convert_tf_to_tradingview(timeframe: str) -> str:
    """
    Convert CCXT timeframe to TradingView interval format
    
    Args:
        timeframe: CCXT format (e.g., '5m', '1h', '1d')
    
    Returns:
        TradingView format (e.g., '5', '60', 'D')
    """
    mapping = {
        '1m': '1',
        '5m': '5',
        '15m': '15',
        '30m': '30',
        '1h': '60',
        '2h': '120',
        '4h': '240',
        '12h': '720',
        '1d': 'D',
        '1w': 'W',
        '1M': 'M'
    }
    
    return mapping.get(timeframe, timeframe.upper().replace('M', ''))


# Example usage
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test with dummy credentials (replace with real ones)
    sender = TelegramSender(
        bot_token='YOUR_BOT_TOKEN',
        chat_id='YOUR_CHAT_ID'
    )
    
    # Test connection
    if sender.test_connection():
        # Create test alert
        test_alert = create_alert_data(
            symbol='BTC/USDT',
            timeframe='5m',
            signal_type='CHoCH Up',
            direction='Long',
            price=67432.50,
            timestamp=datetime.now()
        )
        
        # Send test alert
        sender.send_alert(test_alert)
