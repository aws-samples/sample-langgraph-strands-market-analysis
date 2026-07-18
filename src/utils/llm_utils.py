# Standard library imports
import json
import logging

# Third-party imports
import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from strands.models.bedrock import BedrockModel

# Setup centralized logging
logger = logging.getLogger(__name__)


boto_config = Config(
    retries={"max_attempts": 8, "mode": "adaptive"},
    connect_timeout=5,
    read_timeout=1000,
)
custom_config = Config(region_name="us-east-1")
bedrock_runtime = boto3.client(service_name="bedrock-runtime",
                                region_name="us-east-1")
logger.info(f"Bedrock client region: {bedrock_runtime.meta.region_name}")


MODEL_ID = {
    "claude_3_7": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "claude_4": "us.anthropic.claude-sonnet-4-6",
}


MODELS = {
    "default": "",
    # Sonnet 4.6 uses adaptive thinking with output_config.effort (not budget_tokens)
    "claude-4-thinking-strands": BedrockModel(
        boto_client_config=boto_config,
        model_id=MODEL_ID["claude_4"],
        max_tokens=16000,
        region_name="us-east-1",
        additional_request_fields={
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "high"},
        },
    ),
    "claude-4-interleaved-strands": BedrockModel(
        boto_client_config=boto_config,
        model_id=MODEL_ID["claude_4"],
        max_tokens=16000,
        region_name="us-east-1",
        additional_request_fields={
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "high"},
        },
        cache_prompt="default",
    ),

    "claude-4-strands": BedrockModel(
        model_id=MODEL_ID["claude_4"],
        max_tokens=4000,
        region_name="us-east-1",
        cache_prompt="default",
    ),
    "claude-4-lc": ChatBedrockConverse(
        client=bedrock_runtime,
        model_id=MODEL_ID["claude_4"],
        max_tokens=2000,
    )
}


def invoke_LC_llm_with_prompt(model, prompt) -> str:
    """Generic LLM invocation with error handling"""
    logger.info(f"invoke_LC_llm_with_prompt")
    response = model.invoke(prompt)
    response_text = response.content if hasattr(response, 'content') else str(response)
    
    # Handle different response formats
    if isinstance(response_text, list):
        response_text = response_text[0].get('text', '') if response_text else ''
    logger.info(f"LLM response: {response_text}")
    return response_text


def invoke_STRANDS_llm_with_prompt(model,prompt):
    # Format the request as expected by the model
    logger.info(f"invoke_STRANDS_llm_with_prompt")
    request = model.format_request(
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        system_prompt="You are a helpful assistant."
    )
    
    # Set streaming to False for a direct response
    model.update_config(streaming=False)
    
    # Process all events from the stream
    response_text = ""
    for event in model.stream(request):
        if "contentBlockDelta" in event and "delta" in event["contentBlockDelta"]:
            delta = event["contentBlockDelta"]["delta"]
            if "text" in delta:
                response_text += delta["text"]
    
    return response_text


def parse_llm_json_response(response_text: str) -> dict:
    """Parse a JSON object from an LLM response.

    Tolerant of the common shapes models emit: a bare JSON object, a Markdown
    code fence (```json ... ``` or plain ``` ... ```), or a JSON object embedded
    in surrounding prose. No specific fence or the word "json" is required.
    """
    candidate = response_text.strip()

    # Strip a leading code fence (```json, ```JSON, or bare ```) and its closer.
    if candidate.startswith("```"):
        newline = candidate.find("\n")
        if newline != -1:
            candidate = candidate[newline + 1:]
        if candidate.rstrip().endswith("```"):
            candidate = candidate.rstrip()[:-3]
    candidate = candidate.strip()

    try:
        parsed_response = json.loads(candidate)
    except json.JSONDecodeError:
        # Fall back to the first JSON object embedded anywhere in the text.
        start = candidate.find("{")
        if start < 0:
            raise
        parsed_response, _ = json.JSONDecoder().raw_decode(candidate[start:])

    safe_log_text = "".join(c for c in str(parsed_response)
                            if c.isascii() and (c.isprintable() or c.isspace()))
    logger.info(f"Parsed LLM response: {safe_log_text}")
    return parsed_response


def parse_agent_json_response(response_text):
    """
    Parse the response from the agent into a dict.

    Delegates to parse_llm_json_response, which handles bare JSON, fenced JSON
    (with or without a language tag), and JSON embedded in prose. Returns None
    if no JSON object can be recovered.

    Args:
        response_text: The text response from the agent

    Returns:
        dict: The parsed JSON response, or None if parsing fails
    """
    try:
        return parse_llm_json_response(response_text)
    except Exception as e:
        logger.warning(f"Could not parse JSON from agent response: {type(e).__name__}: {e}")
        return None

def safe_log_text(response: str) -> str:
    safe_text = ''.join(c for c in str(response)
                       if c.isascii()
                       and (c.isprintable()
                            or c.isspace()
                            )
                       )
    return safe_text