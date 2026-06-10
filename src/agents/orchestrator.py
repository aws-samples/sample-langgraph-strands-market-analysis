import logging

# Third-party imports
from strands import Agent

# Local application imports
from src.agents.base_agent import BaseAgent
from src.prompts.system_prompts import ORCHESTRATOR_AGENT_PROMPT
from src.utils.llm_utils import MODELS

# Setup centralized logging
logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Routes user queries to the appropriate set of specialist agents.

    No data-access tools — the orchestrator reasons over the query text and
    returns a JSON routing decision listing which specialists to invoke and
    what specific task to assign each one.
    """

    def __init__(self):
        """Initialize the OrchestratorAgent"""
        logger.info("Initializing OrchestratorAgent")

        super().__init__()

        self.model = MODELS['claude-4-strands']
        self.agent_name = "orchestrator"
        self.system_prompt = ORCHESTRATOR_AGENT_PROMPT
        self.tools = []
        self.callback_handler = None

        logger.info(f"OrchestratorAgent initialized with model: {self.model}")
        logger.debug(f"Agent configuration - name: {self.agent_name}, tools count: {len(self.tools)}")

    def create_agent(self, messages=None, session_id=None):
        """Create an agent with LLM-driven orchestration capabilities"""
        logger.info(f"Creating OrchestratorAgent with session_id: {session_id}")
        logger.debug(f"Agent creation parameters - messages: {len(messages) if messages else 0} messages, model: {self.model}")

        # Set trace attributes for session tracking
        trace_attributes = None
        if session_id:
            trace_attributes = {
                "session_id": session_id,
                "agent_name": self.agent_name
            }
            logger.info(f"Setting trace_attributes: {trace_attributes}")
        else:
            logger.debug("No session_id provided, trace_attributes will be None")

        try:
            agent = Agent(
                model=self.model,
                messages=messages,
                name=self.agent_name,
                system_prompt=self.system_prompt,
                tools=self.tools,
                callback_handler=self.callback_handler,
                trace_attributes=trace_attributes
            )
            logger.info("OrchestratorAgent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create OrchestratorAgent: {e}")
            raise


