import threading
import logging
import json
from flask import Flask, jsonify, render_template, Response
from state import global_state
from utils import get_local_ip

# Initialize Flask server App
flask_app = Flask(__name__)

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
