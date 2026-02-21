import runpy
import sys
import os

# Add the 'src' directory to sys.path
# This ensures that imports like 'from src.gui.gui import SimpleChatApp' resolve correctly
# when app.py is run from the project root.
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Execute src/main.py as the main script
if __name__ == "__main__":
    runpy.run_path(os.path.join(src_path, 'main.py'), run_name='__main__')
