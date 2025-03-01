# Interview AI Navigator

## Overview
Interview AI Navigator is a desktop application that provides real-time coding assistance during practice interview sessions. It monitors your clipboard and provides instant AI-powered hints and suggestions to help you understand and learn from coding problems.

## Features
- **Real-time Clipboard Monitoring**: Automatically detects when new text is copied to your clipboard
- **AI-Powered Assistance**: Utilizes OpenAI's models to provide coding hints and suggestions
- **Multiple AI Model Options**: Choose between different AI models for varied levels of assistance
- **Phone Display Integration**: Built-in Flask server to display responses on your mobile device
- **Always-on-Top Window**: Stays visible while you work on coding problems
- **Toggle Controls**: Easily enable/disable the AI assistance and phone display server

## Requirements
- Python 3.x
- OpenAI API key
- Required Python packages (see requirements.txt)

## Setup
1. Clone this repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
4. Run the application:
   ```
   python interview-solver.py
   ```

## How to Use
1. Launch the application
2. Select your preferred AI model from the dropdown
3. Click "Start Solving Mode" to enable clipboard monitoring
4. Copy any text (like a coding problem) to your clipboard
5. The application will display the copied text and provide AI-generated hints
6. Optionally enable the phone display server to view responses on your mobile device

## Features Explained
- **Solving Mode**: When enabled, the application monitors your clipboard and automatically queries the AI for assistance
- **Phone Display**: Enables a local server that displays AI responses on your phone's browser
- **Model Selection**: Choose between different AI models for varied levels of assistance:
  - gpt-4o-mini: Faster, more concise responses
  - gpt-4o: More detailed assistance
  - o1: Advanced model for complex problems

## Technical Details
- Built with Python and Tkinter for the GUI
- Uses OpenAI's API for generating responses
- Implements Flask for mobile device integration
- Runs a local server for phone display functionality
- Features thread-safe operations for smooth performance

## Note
This tool is designed as a learning aid to help understand coding problems and concepts. It should not be used during actual interviews or assessments. Always ensure you comply with your institution's academic integrity policies.

**⚠️ Disclaimer: This tool is for educational purposes only.**