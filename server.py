import threading
import logging
from flask import Flask, jsonify
from state import global_state
from utils import get_local_ip

# Initialize Flask server App
flask_app = Flask(__name__)

@flask_app.route('/response', methods=['GET'])
def get_response():
    """Flask endpoint to serve the latest response."""
    return jsonify({"response": global_state.latest_response})

def run_flask_app(host="0.0.0.0", port=5000):
    """Runs the Flask app."""
    # Note: app.run is blocking, so this is intended to be run in a thread
    flask_app.run(host=host, port=port, debug=False, use_reloader=False)

def start_server_thread(host="0.0.0.0", port=5000):
    """Starts the Flask server in a daemon thread."""
    server_thread = threading.Thread(
        target=run_flask_app,
        kwargs={"host": host, "port": port},
        daemon=True
    )
    server_thread.start()
    return server_thread
