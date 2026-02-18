import os
import logging
import openai
from dotenv import load_dotenv

class LLMService:
    SYSTEM_PROMPTS = {
        "default": "You are an expert programming assistant. Provide simple commenting, hints, and code response only.",
        "interview": """You are an expert Data Science and Deep Learning Interview assistant. 
        Your goal is to help the user act NATURAL and EXPERT. 
        Structure your response into these sections:
        1. CONCEPT: A 1-sentence explanation of the ML/DS theory (e.g., Why Random Forest? What is LoRA? Why use a linear transform?).
        2. STRATEGIC HINT TO ASK: Provide a smart question the user can ask the interviewer to 'get a hint' and look natural (e.g., "I'm thinking about X, but should I consider Y?").
        3. TALKING POINTS: 2-3 bullet points to say out loud while 'thinking'.
        4. CODE/SQL: The optimized solution. Use Pandas, SQL, or PyTorch (LoRA/NN) as requested.
        Keep it concise and tactical."""
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
        """Queries the OpenAI API and yields response chunks.
        
        Args:
            prompt: The user prompt to send to the API
            model: The model to use (default: gpt-4o-mini)
            
        Yields:
            str: Chunks of the API response
        """
        if not self.client:
            yield "Error: OpenAI Client not initialized. Check API Key."
            return
        
        # Validate input prompt
        if not prompt or not isinstance(prompt, str) or len(prompt.strip()) < 2:
            yield "Error: Invalid prompt provided. Please provide meaningful input."
            return
        
        # Validate model name
        if not model or not isinstance(model, str):
            yield "Error: Invalid model specified."
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
            
            chunk_count = 0
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        chunk_count += 1
                        yield delta_content
            
            if chunk_count == 0:
                yield "(No response from API)"
                logging.warning("API stream returned no content chunks")

        except openai.APIConnectionError as e:
            error_msg = f"Connection Error: Could not reach OpenAI servers. {str(e)[:80]}"
            logging.error(error_msg)
            yield f"Error: {error_msg}"
        except openai.RateLimitError as e:
            error_msg = "Error: Rate limit exceeded. Please wait a moment and try again."
            logging.error(f"Rate limit error: {e}")
            yield error_msg
        except openai.AuthenticationError as e:
            error_msg = "Error: Invalid API Key. Please check your configuration."
            logging.error(f"Authentication error: {e}")
            yield error_msg
        except openai.APIStatusError as e:
            error_msg = f"API Error (Status {e.status_code}): {str(e.message)[:80]}"
            logging.error(error_msg)
            yield f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)[:80]}"
            logging.exception("An unexpected error occurred during streaming API call")
            yield f"Error: {error_msg}"
