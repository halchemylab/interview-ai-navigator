import os
import logging
import openai
from dotenv import load_dotenv

class LLMService:
    SYSTEM_PROMPTS = {
        "default": "You are an expert programming assistant. Provide simple commenting, hints, and code response only.",
        "interview": """You are an expert Data Science and Technical Interview assistant. 
        Structure your response into 3 CLEAR sections:
        1. LOGIC: A brief explanation of the approach. For DS: Mention the specific algorithm, SQL join type, or Pandas method used (1-2 sentences).
        2. PSEUDOCODE: Simple logic steps to guide the implementation.
        3. CODE: The optimized solution (Python/Pandas/SQL). 
        Always aim for memory-efficient and readable code. Keep it concise."""
    }

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        self.model = "gpt-4o-mini"
        self.current_prompt_mode = "interview" # Default to interview mode for this project
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
            {"role": "system", "content": self.SYSTEM_PROMPTS.get(self.current_prompt_mode, self.SYSTEM_PROMPTS["default"])},
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
            return f"Error: Could not connect to OpenAI API.\n{e}"
        except openai.RateLimitError as e:
            error_msg = f"Rate Limit Error: {e}"
            logging.error(error_msg)
            return f"Error: Rate limit exceeded. Please wait and try again.\n{e}"
        except openai.AuthenticationError as e:
             error_msg = f"Authentication Error: {e}"
             logging.error(error_msg)
             return f"Error: Invalid OpenAI API Key.\nCheck your .env file.\n{e}"
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            logging.exception("An unexpected error occurred during API call")
            return f"Error querying API: {error_msg}"

    def query_api_stream(self, prompt, model="gpt-4o-mini"):
        """Queries the OpenAI API and yields response chunks."""
        if not self.client:
            yield "Error: OpenAI Client not initialized. Check API Key."
            return

        logging.info(f"Sending streaming query to model: {model}")
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPTS.get(self.current_prompt_mode, self.SYSTEM_PROMPTS["default"])},
            {"role": "user", "content": prompt}
        ]
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.6,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logging.exception("An unexpected error occurred during streaming API call")
            yield f"Error querying API: {str(e)}"
