import os
import logging
import openai
from dotenv import load_dotenv

class LLMService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the OpenAI client."""
        if not self.api_key:
            logging.error("OpenAI API key not found in .env file")
            self.client = None
            return

        try:
            self.client = openai.OpenAI(api_key=self.api_key)
        except Exception as e:
            logging.exception("Failed to initialize OpenAI client")
            self.client = None

    def update_api_key(self, new_key):
        """Updates the API key and re-initializes the client."""
        self.api_key = new_key
        # Update the environment variable in the current process
        os.environ['OPENAI_API_KEY'] = new_key 
        self._initialize_client()

    def query_api(self, prompt, model="gpt-4o-mini"):
        """Queries the OpenAI API and returns the response text."""
        if not self.client:
            return "Error: OpenAI Client not initialized. Check API Key."

        logging.info(f"Sending query to model: {model}")
        messages = [
            {"role": "system", "content": "You are an expert programming assistant. Provide simple commenting, hints, and code response only."},
            {"role": "user", "content": prompt}
        ]
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.6
            )
            output = response.choices[0].message.content.strip()
            logging.info("API response successfully received.")
            return output

        except openai.APIConnectionError as e:
            error_msg = f"Connection Error: {e}"
            logging.error(error_msg)
            return f"Error: Could not connect to OpenAI API.
{e}"
        except openai.RateLimitError as e:
            error_msg = f"Rate Limit Error: {e}"
            logging.error(error_msg)
            return f"Error: Rate limit exceeded. Please wait and try again.
{e}"
        except openai.AuthenticationError as e:
             error_msg = f"Authentication Error: {e}"
             logging.error(error_msg)
             return f"Error: Invalid OpenAI API Key.
Check your .env file.
{e}"
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            logging.exception("An unexpected error occurred during API call")
            return f"Error querying API: {error_msg}"
