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
    """Parse and clean LLM JSON response"""
    # Clean up response text and extract JSON
    response_text = response_text.strip()
    if response_text.startswith('```json'):
        response_text = response_text[7:]
    if response_text.endswith('```'):
        response_text = response_text[:-3]
    
    parsed_response = json.loads(response_text.strip())
    safe_log_text = "".join(c for c in str(parsed_response)
                            if c.isascii() and (c.isprintable() or c.isspace()))
    logger.info(f"Parsed LLM response: {safe_log_text}")
    return parsed_response


def parse_agent_json_response(response_text):
    """
    Parse the response from the agent, handling both pure JSON and JSON embedded in Markdown.
    
    Args:
        response_text: The text response from the agent
    
    Returns:
        dict: The parsed JSON response or the original text if parsing fails
    """
    # Check if the response contains a JSON code block
    try:
        if "```json" in response_text and "```" in response_text:
            # Extract the JSON content from the code block including the markers
            # so parse_llm_json_response can handle them properly
            start_index = response_text.find("```json")
            end_index = response_text.find("```", start_index + 7) + 3
            json_str = response_text[start_index:end_index].strip()
            
            logger.info(f"Extracted JSON block from markdown: {json_str[:100]}...")
            respone = parse_llm_json_response(json_str)
            logger.info("Successfully parsed JSON block from agent response")
            return respone
        else:
            # If no JSON block, try to parse the entire response as JSON
            logger.info("No JSON block found, attempting to parse full response")
            return parse_llm_json_response(response_text)
    except:
        pass

def safe_log_text(response: str) -> str:
    safe_text = ''.join(c for c in str(response)
                       if c.isascii()
                       and (c.isprintable()
                            or c.isspace()
                            )
                       )
    return safe_text