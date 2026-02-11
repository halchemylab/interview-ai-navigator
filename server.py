import threading
import logging
import json
from flask import Flask, jsonify, render_template, Response, request
from state import global_state
from utils import get_local_ip

from werkzeug.serving import make_server

# Initialize Flask server App
flask_app = Flask(__name__)

# Global server instance
_server_instance = None

@flask_app.route('/')
def index():
    """Serves the mobile-friendly dashboard."""
    return render_template('index.html')

@flask_app.route('/response', methods=['GET'])
def get_response():
    """Flask endpoint to serve the latest response."""
    return jsonify({"response": global_state.latest_response})

@flask_app.route('/stream')
def stream():
    """Server-Sent Events endpoint to push updates to the client."""
    def event_stream():
        # Send the current response immediately upon connection
        initial_data = json.dumps({"response": global_state.latest_response})
        yield f"data: {initial_data}\n\n"
        
        while True:
            # Wait for an update notification from the GUI thread
            global_state.wait_for_update()
            
            # Fetch the new data
            data = json.dumps({"response": global_state.latest_response})
            yield f"data: {data}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")

@flask_app.route('/test_connection', methods=['POST'])
def test_connection():
    """Endpoint to receive test messages from the desktop app."""
    try:
        data = request.get_json()
        message = data.get("message", "Test message received!")
        global_state.update_response(f"Phone Display Test: {message}")
        logging.info(f"Received test message for phone display: {message}")
        return jsonify({"status": "success", "received_message": message}), 200
    except Exception as e:
        logging.error(f"Error processing test connection request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

class ServerThread(threading.Thread):
    def __init__(self, app, host, port):
        threading.Thread.__init__(self, daemon=True)
        self.srv = make_server(host, port, app, threaded=True)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        logging.info("Starting Flask server...")
        self.srv.serve_forever()

    def shutdown(self):
        logging.info("Shutting down Flask server...")
        self.srv.shutdown()

def start_server(host="0.0.0.0", port=5000):
    """Starts the Flask server if not already running."""
    global _server_instance
    if _server_instance and _server_instance.is_alive():
        logging.warning("Server is already running.")
        return _server_instance

    _server_instance = ServerThread(flask_app, host, port)
    _server_instance.start()
    return _server_instance

def stop_server():
    """Gracefully stops the running Flask server."""
    global _server_instance
    if _server_instance:
        _server_instance.shutdown()
        _server_instance.join(timeout=2)
        _server_instance = None
        logging.info("Server stopped successfully.")
    else:
        logging.warning("No server instance to stop.")
