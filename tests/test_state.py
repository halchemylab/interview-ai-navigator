import unittest
from src.core.state import AppState, global_state

class TestAppState(unittest.TestCase):
    def test_initial_state(self):
        state = AppState()
        self.assertEqual(state.latest_response, "No response yet.")

    def test_global_state_exists(self):
        self.assertIsInstance(global_state, AppState)

if __name__ == '__main__':
    unittest.main()
