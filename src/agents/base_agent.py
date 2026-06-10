# Standard library imports
import logging
from typing import List, Dict, Any, TypedDict, Optional

# Setup centralized logging
logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for agents with common functionality"""

    def __init__(self):
        """Initialize the base agent"""
        logger.info("Initializing BaseAgent")
        self.model = None
        self.agent_name = None
        self.system_prompt = None
        self.tools = []
        self.callback_handler = None
        logger.debug("BaseAgent initialization completed")

    def create_agent(self, messages=None, session_id=None):
        """Create an agent with specified model and tools"""
        raise NotImplementedError("Subclasses should implement this method")

    def chat(self):
        """Interactive chat mode"""
        logger.info("Starting chat mode")
        agent = self.create_agent()

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    logger.info("Exiting chat mode")
                    break

                if not query:
                    continue

                logger.info(f"Processing query: {query}")
                result = agent(query)

                if hasattr(result, '__str__'):
                    logger.info(f"Response Type:{type(result)}")
                    safe_log_text = ''.join(c for c in str(result) if c.isascii() and (c.isprintable() or c.isspace()))
                    logger.info(f"Query processed successfully:{safe_log_text}")
            except KeyboardInterrupt:
                logger.info("Chat interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in chat mode: {e}")
                logger.error(f"Error: {e}")

    def execute(self, query, session_id=None):
        """Execute single predefined query"""
        logger.info("Starting execute query mode")
        agent = self.create_agent(session_id=session_id)

        logger.info(f"Executing query: {query}")
        try:
            result = agent(query)
            if hasattr(result, '__str__'):
                logger.info(f"Response Type:{type(result)}")
                safe_log_text = ''.join(c for c in str(result) if c.isascii() and (c.isprintable() or c.isspace()))
            logger.info(f"Query processed successfully:{safe_log_text}")
            return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Error: {e}")
            return None  # Return None on error
