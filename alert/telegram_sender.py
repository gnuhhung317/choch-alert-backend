"""
Telegram Alert Sender - Send formatted CHoCH alerts via Telegram Bot API
"""
import requests
import logging
from typing import Dict, Optional
from datetime import datetime
from utils.tradingview_helper import generate_tradingview_link

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
            alert_data: Dict with keys: time_date, mã, khung, hướng, loại, price, tradingview_link
        
        Returns:
            Formatted message string
        """
        # Format price with appropriate decimals
        price = alert_data.get('price', 0)
        
        # Better price formatting based on price range
        if price == 0:
            price_str = "N/A"
        elif price < 0.001:
            price_str = f"${price:.8f}"  # Very small prices (like NEIRO)
        elif price < 0.01:
            price_str = f"${price:.6f}"
        elif price < 1:
            price_str = f"${price:.4f}"
        elif price < 100:
            price_str = f"${price:.3f}"
        else:
            price_str = f"${price:,.2f}"
        
        # Get TradingView link
        tv_link = alert_data.get('tradingview_link', '#')
        
        message = (
            f"🚨 *CHoCH SIGNAL DETECTED* 🚨\n\n"
            f"⏰ *Time:* {alert_data.get('time_date', 'N/A')}\n"
            f"💰 *Mã:* {alert_data.get('mã', 'N/A')}\n"
            f"📊 *Khung:* {alert_data.get('khung', 'N/A')}\n"
            f"📈 *Hướng:* {alert_data.get('hướng', 'N/A')}\n"
            f"🎯 *Loại:* {alert_data.get('loại', 'N/A')}\n"
            f"💵 *Price:* {price_str}\n\n"
            f"🔗 [View on TradingView]({tv_link})"
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
    def send_message(self, message: str, parse_mode: Optional[str] = 'Markdown') -> bool:
        """
        Send a custom message to Telegram
        
        Args:
            message: Message text to send
            parse_mode: Optional parse mode (e.g., 'Markdown', 'HTML')
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Message sent to Telegram")
                return True
            else:
                logger.error(f"❌ Failed to send Telegram message: {response.status_code} - {response.text}")
                return False
        
        except requests.RequestException as e:
            logger.error(f"❌ Telegram API request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending Telegram message: {e}")
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
                     direction: str, price: float, timestamp: datetime,
                     pattern_group: str = None) -> Dict:
    """
    Create alert data dictionary
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        timeframe: Timeframe (e.g., '5m', '1h')
        signal_type: Signal type (e.g., 'CHoCH Up')
        direction: Direction ('Long' or 'Short')
        price: Current price
        timestamp: Signal timestamp
        pattern_group: Pattern group (G1, G2, G3)
    
    Returns:
        Alert data dictionary with TradingView link
    """
    # Generate TradingView link
    tv_link = generate_tradingview_link(
        symbol=symbol,
        timeframe=timeframe,
        is_futures=True,
        region='in'
    )
    
    return {
        'time_date': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol,
        'mã': symbol,
        'khung': timeframe,
        'hướng': direction,  # Should be 'Long' or 'Short'
        'nhóm': pattern_group,  # Pattern group (G1, G2, G3)
        'loại': signal_type,
        'price': price,
        'tradingview_link': tv_link
    }


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
