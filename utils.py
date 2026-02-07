import socket
import logging

def get_local_ip():
    """Attempts to get the local IP address connected to the internet."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually send data, just finds preferred route
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip
    except socket.error as e:
        logging.warning(f"Could not determine local IP: {e}. Using 127.0.0.1")
        return "127.0.0.1" # Fallback
    finally:
        if s:
            s.close()
