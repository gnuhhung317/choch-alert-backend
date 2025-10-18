"""
Flask Web Application with SocketIO for real-time alert display
"""
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import logging
from typing import Dict
import threading

logger = logging.getLogger(__name__)

# Global variables for Flask app and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'choch-alert-secret-key-change-in-production'
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store alerts in memory (last 100)
alerts_history = []
MAX_ALERTS = 100


@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'alerts_count': len(alerts_history)}


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f'Client connected')
    # Send recent alerts to newly connected client
    emit('alerts_history', alerts_history)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')


@socketio.on('request_history')
def handle_request_history():
    """Send alert history to client"""
    emit('alerts_history', alerts_history)


def broadcast_alert(alert_data: Dict):
    """
    Broadcast alert to all connected clients
    
    Args:
        alert_data: Alert data dictionary
    """
    try:
        # Add to history
        alerts_history.insert(0, alert_data)  # Insert at beginning
        
        # Keep only last MAX_ALERTS
        if len(alerts_history) > MAX_ALERTS:
            alerts_history[:] = alerts_history[:MAX_ALERTS]
        
        # Broadcast to all clients
        socketio.emit('alert', alert_data, broadcast=True)
        logger.info(f"📡 Broadcasted alert: {alert_data.get('loại')} on {alert_data.get('khung')}")
    
    except Exception as e:
        logger.error(f"Error broadcasting alert: {e}")


def run_flask_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """
    Run Flask app with SocketIO
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Debug mode
    """
    logger.info(f"🌐 Starting Flask web server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


def start_flask_background(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """
    Start Flask app in background thread
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Debug mode
    """
    thread = threading.Thread(
        target=run_flask_app,
        args=(host, port, debug),
        daemon=True
    )
    thread.start()
    logger.info("Flask app started in background thread")
    return thread


# Export for use in main.py
__all__ = ['app', 'socketio', 'broadcast_alert', 'run_flask_app', 'start_flask_background']


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_flask_app(debug=True)
