# Interview Solver

An application that simulates an interview assistance tool enhanced by the ChatGPT API. This tool is designed for educational purposes and demonstration only.

## Features

- **Screen Capture:** Capture and save screenshots of your primary display
- **Companion Mode:** Display code and chat results on a secondary device via a web server
- **Hotkey Functionality:** Use Ctrl+Shift+Q to query ChatGPT with selected text
- **ChatGPT Integration:** Send queries to OpenAI's ChatGPT API and display responses
- **Simple GUI:** Easy-to-use interface with all core functionality accessible

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Replace the placeholder API key in the code with your actual OpenAI API key:

```python
# Replace this with your actual OpenAI API key
OPENAI_API_KEY = "your_openai_api_key_here"
```

## Usage

1. Run the application:

```bash
python interview_solver.py
```

2. The main GUI window will appear with the following features:
   - **Capture Screen:** Take a screenshot of your display
   - **Start Companion Mode:** Start the web server for second-screen display
   - **Companion Mode URL:** URL to access on your secondary device
   - **Selected Text Area:** Shows text selected when hotkey is pressed
   - **ChatGPT Response Area:** Shows the API response

3. To use the application during an interview simulation:
   - Press Ctrl+Shift+Q to send selected text to ChatGPT
   - View responses in the main application
   - Use Companion Mode on a second device to discreetly view responses

## How It Works

1. **Screen Capture:** Uses PIL/Pillow to capture the screen
2. **Hotkey Handling:** Registers global hotkeys with pynput
3. **Text Selection:** Gets selected text via clipboard
4. **API Integration:** Sends queries to OpenAI's ChatGPT API
5. **Companion Mode:** Runs a Flask web server that can be accessed from other devices

## Note

This application is for educational and demonstration purposes only. It should not be used in actual interviews or assessment situations where such tools would be considered cheating.

## Requirements

- Python 3.6 or higher
- Dependencies listed in requirements.txt
- OpenAI API key
