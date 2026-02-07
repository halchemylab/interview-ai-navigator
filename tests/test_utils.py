import unittest
from unittest.mock import patch, MagicMock
import socket
from utils import get_local_ip

class TestUtils(unittest.TestCase):
    @patch('socket.socket')
    def test_get_local_ip_success(self, mock_socket_cls):
        # Setup mock
        mock_socket_instance = MagicMock()
        mock_socket_cls.return_value = mock_socket_instance
        # when getsockname is called, return a tuple (ip, port)
        mock_socket_instance.getsockname.return_value = ('192.168.1.5', 12345)

        ip = get_local_ip()
        self.assertEqual(ip, '192.168.1.5')
        
        # Verify calls
        mock_socket_cls.assert_called_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_socket_instance.connect.assert_called_with(("8.8.8.8", 80))
        mock_socket_instance.close.assert_called()

    @patch('socket.socket')
    def test_get_local_ip_failure(self, mock_socket_cls):
        # Simulate socket creation failure
        mock_socket_cls.side_effect = socket.error("Mock socket error")

        ip = get_local_ip()
        self.assertEqual(ip, '127.0.0.1')

if __name__ == '__main__':
    unittest.main()
