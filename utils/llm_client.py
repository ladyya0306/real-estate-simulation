import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import logging

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Setup Logger
logger = logging.getLogger(__name__)

if not API_KEY:
    logger.warning("DEEPSEEK_API_KEY not found in environment variables. LLM calls will fail.")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def call_llm(prompt: str, system_prompt: str = "You are a helpful assistant in a real estate simulation.") -> str:
    """
    Call DeepSeek API via OpenAI SDK.
    """
    if not API_KEY:
        return "Error: No API Key Provided"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        return f"Error: {str(e)}"

def safe_call_llm(prompt: str, default_return: dict, system_prompt: str = "") -> dict:
    """
    Call LLM and parse JSON response. Returns default if failure.
    Appends 'Respond in JSON format.' to prompt.
    """
    json_prompt = prompt + "\n\n请只输出JSON格式，不要包含Markdown代码块或其他文本。"
    
    response_text = call_llm(json_prompt, system_prompt)
    
    # Try to clean markdown code blocks if present
    clean_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON. Response: {response_text}")
        # Attempt to find substrings
        try:
             start = clean_text.find('{')
             end = clean_text.rfind('}')
             if start != -1 and end != -1:
                 return json.loads(clean_text[start:end+1])
        except:
            pass
        return default_return
