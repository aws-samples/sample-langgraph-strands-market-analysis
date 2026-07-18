"""
Market Surveillance Workflow for AWS AgentCore
Uses BedrockAgentCoreApp for proper AgentCore integration
"""

import logging
import os

from dotenv import load_dotenv
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from src.agents import Workflow
from src.config.logging_config import configure_logging

# Load environment variables
load_dotenv()

# Configure logging for AgentCore (logs go to CloudWatch, no file logging)
configure_logging(force_console=True)
logger = logging.getLogger(__name__)

# Create AgentCore app
app = BedrockAgentCoreApp()

# Initialize workflow
try:
    logger.info("Initializing Market Surveillance Workflow for AgentCore runtime...")
    workflow = Workflow()
    logger.info("Workflow initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize workflow: {type(e).__name__}: {str(e)}")
    raise


@app.entrypoint
async def market_surveillance_workflow(payload):
    """
    Main entrypoint for AgentCore invocations
    
    Args:
        payload: Dictionary containing:
            - prompt: User query
            - session_id: Session identifier for conversation continuity
              (maps to the AgentCore Memory thread/session)
            - actor_id: Optional actor identifier (defaults to "default-actor";
              required by AgentCore Memory to scope checkpoints per actor)
    
    Yields:
        Streaming response chunks from the workflow
    """
    try:
        # Extract parameters from payload
        prompt = payload.get("prompt")
        session_id = payload.get("session_id", "default-session")
        actor_id = payload.get("actor_id", "default-actor")

        logger.info(f"Workflow invocation - session: {session_id}, actor: {actor_id}")

        if not prompt:
            yield "Error: No prompt provided in payload"
            return

        # Stream workflow response
        async for chunk in workflow.stream_query(
            session_id=session_id,
            prompt=prompt,
            actor_id=actor_id
        ):
            yield chunk
            
    except Exception as e:
        error_msg = f"Error in workflow execution: {str(e)}"
        logger.error(error_msg)
        yield error_msg


if __name__ == "__main__":
    logger.info("Starting Market Surveillance Workflow AgentCore runtime...")
    app.run()