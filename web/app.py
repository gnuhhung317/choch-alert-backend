"""
Flask Web Application with SocketIO for real-time alert display
Now with SQLite database storage
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import logging
from typing import Dict, List
import threading
import os
import sys
from datetime import datetime, timedelta
import pytz

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.alert_db import AlertDatabase, get_database

logger = logging.getLogger(__name__)

# Global variables for Flask app and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'choch-alert-secret-key-change-in-production'
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize database
db = get_database('data/choch_alerts.db')

# Maximum alerts per page
MAX_ALERTS_PER_PAGE = 50
# Maximum alerts to fetch from API
MAX_ALERTS_FETCH = 500

# GMT+7 timezone
GMT7 = pytz.timezone('Asia/Bangkok')


@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        stats = db.get_alert_stats()
        return {
            'status': 'ok', 
            'alerts_count': stats.get('total_alerts', 0),
            'database': 'connected'
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'error', 'message': str(e)}, 500


@app.route('/api/alerts')
def get_alerts():
    """API endpoint to get alerts with filtering"""
    try:
        # Get query parameters - Max 500 for initial load, 50 per page for display
        limit = min(int(request.args.get('limit', MAX_ALERTS_PER_PAGE)), MAX_ALERTS_FETCH)
        offset = int(request.args.get('offset', 0))
        
        # Filter parameters
        symbols = request.args.getlist('symbol')
        timeframes = request.args.getlist('timeframe') 
        directions = request.args.getlist('direction')
        signal_types = request.args.getlist('signal_type')
        date_filter = request.args.get('date_filter', '')  # 'today' or empty
        
        # Get filtered alerts
        if any([symbols, timeframes, directions, signal_types]):
            alerts = db.filter_alerts(
                symbols=symbols if symbols else None,
                timeframes=timeframes if timeframes else None,
                directions=directions if directions else None,
                signal_types=signal_types if signal_types else None,
                limit=limit,
                offset=offset
            )
        else:
            alerts = db.get_recent_alerts(limit=limit, offset=offset)
        
        # Apply date filter if needed
        if date_filter == 'today':
            # Get today's date in GMT+7
            now_gmt7 = datetime.now(GMT7)
            today_start = now_gmt7.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Filter alerts from today
            alerts = [alert for alert in alerts 
                     if datetime.fromisoformat(alert['time_date'].replace('Z', '+00:00')).astimezone(GMT7) >= today_start]
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/stats')
def get_alert_statistics():
    """API endpoint for alert statistics"""
    try:
        stats = db.get_alert_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/unique-values')
def get_unique_values():
    """API endpoint for unique filter values"""
    try:
        unique_values = db.get_unique_values()
        return jsonify(unique_values)
    except Exception as e:
        logger.error(f"Error getting unique values: {e}")
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f'Client connected')
    # Send recent alerts to newly connected client (max 50)
    try:
        recent_alerts = db.get_recent_alerts(limit=MAX_ALERTS_PER_PAGE)
        emit('alerts_history', recent_alerts)
        logger.info(f"Sent {len(recent_alerts)} recent alerts to new client")
    except Exception as e:
        logger.error(f"Error sending alerts to new client: {e}")
        emit('alerts_history', [])


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')


@socketio.on('request_history')
def handle_request_history():
    """Send alert history to client (max 50)"""
    try:
        recent_alerts = db.get_recent_alerts(limit=MAX_ALERTS_PER_PAGE)
        emit('alerts_history', recent_alerts)
        logger.info(f"Sent {len(recent_alerts)} alerts on history request")
    except Exception as e:
        logger.error(f"Error sending alert history: {e}")
        emit('alerts_history', [])


def broadcast_alert(alert_data: Dict):
    """
    Broadcast alert to all connected clients and save to database
    
    Args:
        alert_data: Alert data dictionary
    """
    try:
        # Save alert to database
        saved_alert = db.add_alert(alert_data)
        if saved_alert:
            # Convert to dict format for broadcasting
            alert_dict = saved_alert.to_dict()
            
            # Broadcast to all clients (use namespace='/' instead of broadcast=True for external calls)
            socketio.emit('alert', alert_dict, namespace='/')
            logger.info(f"📡 Broadcasted alert: {alert_data.get('loại')} on {alert_data.get('khung')} - Saved to DB with ID {saved_alert.id}")
        else:
            # Fallback: broadcast original data even if DB save failed
            socketio.emit('alert', alert_data, namespace='/')
            logger.warning(f"📡 Broadcasted alert without DB save: {alert_data.get('loại')} on {alert_data.get('khung')}")
    
    except Exception as e:
        logger.error(f"Error broadcasting alert: {e}")
        # Try to broadcast anyway
        try:
            socketio.emit('alert', alert_data, namespace='/')
        except Exception as e2:
            logger.error(f"Failed to broadcast alert at all: {e2}")


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


def cleanup_database():
    """Cleanup old alerts from database"""
    try:
        archived_count = db.cleanup_old_alerts(days_to_keep=30)
        logger.info(f"Database cleanup: archived {archived_count} old alerts")
        return archived_count
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
        return 0


def shutdown_database():
    """Gracefully shutdown database connections"""
    try:
        db.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Cleanup handler for graceful shutdown
import atexit
atexit.register(shutdown_database)


# Export for use in main.py
__all__ = [
    'app', 'socketio', 'broadcast_alert', 'run_flask_app', 'start_flask_background',
    'cleanup_database', 'shutdown_database', 'db'
]


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test database connection
    try:
        stats = db.get_alert_stats()
        logger.info(f"Database connected successfully. Total alerts: {stats.get('total_alerts', 0)}")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        exit(1)
    
    # Run flask app
    run_flask_app(debug=True)
