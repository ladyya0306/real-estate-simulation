import os
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI
import json
import logging

# Load environment variables
load_dotenv()

# Configuration
# Configuration
load_dotenv()

# --- 1. Smart Model Config (Default/Primary) ---
SMART_API_KEY = os.getenv("SMART_API_KEY", os.getenv("DEEPSEEK_API_KEY"))
SMART_BASE_URL = os.getenv("SMART_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
MODEL_SMART = os.getenv("MODEL_SMART", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))

# --- 2. Fast Model Config (Secondary) ---
# If FAST keys are not set, fallback to SMART keys (Aggregation Gateway scenario)
FAST_API_KEY = os.getenv("FAST_API_KEY", SMART_API_KEY)
FAST_BASE_URL = os.getenv("FAST_BASE_URL", SMART_BASE_URL)
MODEL_FAST = os.getenv("MODEL_FAST", MODEL_SMART)

# Setup Logger
logger = logging.getLogger(__name__)

if not SMART_API_KEY:
    logger.warning("SMART_API_KEY (or DEEPSEEK_API_KEY) not found. Main LLM calls will fail.")

# Initialize Clients
# Smart Clients
client_smart = OpenAI(api_key=SMART_API_KEY, base_url=SMART_BASE_URL)
aclient_smart = AsyncOpenAI(api_key=SMART_API_KEY, base_url=SMART_BASE_URL)

# Fast Clients (Reuse Smart clients if config is identical to save resources)
if FAST_API_KEY == SMART_API_KEY and FAST_BASE_URL == SMART_BASE_URL:
    client_fast = client_smart
    aclient_fast = aclient_smart
else:
    client_fast = OpenAI(api_key=FAST_API_KEY, base_url=FAST_BASE_URL)
    aclient_fast = AsyncOpenAI(api_key=FAST_API_KEY, base_url=FAST_BASE_URL)

def get_client(model_type: str, is_async: bool = False):
    """Select appropriate client based on model type."""
    if model_type.lower() == "fast":
        return aclient_fast if is_async else client_fast
    return aclient_smart if is_async else client_smart

def get_model_id(model_type: str) -> str:
    """Select model ID based on type."""
    if model_type.lower() == "fast":
        return MODEL_FAST
    return MODEL_SMART

def call_llm(prompt: str, system_prompt: str = "You are a helpful assistant in a real estate simulation.", json_mode: bool = False, model_type: str = "smart") -> str:
    """
    Call LLM via OpenAI SDK (Supports Dual Providers).
    model_type: 'smart' (default) or 'fast'
    """
    current_client = get_client(model_type, is_async=False)
    
    try:
        kwargs = {
            "model": get_model_id(model_type),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "temperature": 0.7
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = current_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM Call Failed ({model_type}): {e}")
        return f"Error: {str(e)}"

def safe_call_llm(prompt: str, default_return: dict, system_prompt: str = "", model_type: str = "smart") -> dict:
    """
    Call LLM and parse JSON response. Returns default if failure.
    """
    json_prompt = prompt + "\n\n请只输出JSON格式，不要包含Markdown代码块或其他文本。"
    
    response_text = call_llm(json_prompt, system_prompt, json_mode=True, model_type=model_type)
    
    clean_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON. Response: {response_text}")
        try:
             start = clean_text.find('{')
             end = clean_text.rfind('}')
             if start != -1 and end != -1:
                 return json.loads(clean_text[start:end+1])
        except:
            pass
        return default_return

async def call_llm_async(prompt: str, system_prompt: str = "You are a helpful assistant in a real estate simulation.", json_mode: bool = False, model_type: str = "smart") -> str:
    """
    Async Call LLM via OpenAI SDK (Supports Dual Providers).
    """
    current_client = get_client(model_type, is_async=True)

    try:
        kwargs = {
            "model": get_model_id(model_type),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "temperature": 0.7
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await current_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Async LLM Call Failed ({model_type}): {e}")
        return f"Error: {str(e)}"

async def safe_call_llm_async(prompt: str, default_return: dict, system_prompt: str = "", model_type: str = "smart") -> dict:
    """
    Async wrapper for safe JSON LLM calls.
    """
    json_prompt = prompt + "\n\n请只输出JSON格式，不要包含Markdown代码块或其他文本。"
    
    response_text = await call_llm_async(json_prompt, system_prompt, json_mode=True, model_type=model_type)
    
    clean_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON (Async). Response: {response_text}")
        try:
             start = clean_text.find('{')
             end = clean_text.rfind('}')
             if start != -1 and end != -1:
                 return json.loads(clean_text[start:end+1])
        except:
            pass
        return default_return

