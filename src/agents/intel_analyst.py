import logging
from strands import Agent
from strands_tools import http_request
from src.agents.base_agent import BaseAgent
from src.prompts.system_prompts import INTEL_ANALYST_AGENT_PROMPT
from src.utils.llm_utils import MODELS

logger = logging.getLogger(__name__)


class IntelAnalystAgent(BaseAgent):
    """Gathers external market intelligence via online research.

    Has access to: http_request tool for public web sources.
    Retrieves regulatory news, company announcements, and macro events
    that provide context for unusual market activity.
    """

    def __init__(self):
        logger.info("Initializing IntelAnalystAgent")
        super().__init__()
        self.model = MODELS['claude-4-interleaved-strands']
        self.agent_name = "intel_analyst"
        self.system_prompt = INTEL_ANALYST_AGENT_PROMPT
        self.tools = [http_request]
        self.callback_handler = None
        logger.info(f"IntelAnalystAgent initialized with model: {self.model}")

    def create_agent(self, messages=None, session_id=None):
        logger.info(f"Creating IntelAnalystAgent with session_id: {session_id}")
        trace_attributes = None
        if session_id:
            trace_attributes = {"session_id": session_id, "agent_name": self.agent_name}
        try:
            agent = Agent(
                model=self.model, messages=messages, name=self.agent_name,
                system_prompt=self.system_prompt, tools=self.tools,
                callback_handler=self.callback_handler, trace_attributes=trace_attributes
            )
            logger.info("IntelAnalystAgent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create IntelAnalystAgent: {e}")
            raise
