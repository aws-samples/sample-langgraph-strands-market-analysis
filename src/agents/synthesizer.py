# Standard library imports
import logging
import os

# Third-party imports
from strands import Agent

# Local application imports
from src.agents.base_agent import BaseAgent
from src.utils.llm_utils import MODELS

# Setup centralized logging
logger = logging.getLogger(__name__)


class SynthesizerAgent(BaseAgent):
    """Combines specialist agent insights into a structured final response.

    No tools — reads the accumulated insights from all specialists in the
    LangGraph state and synthesises them into a coherent, factual summary
    for the end user.
    """

    def __init__(self):
        """Initialize the SynthesizerAgent"""
        logger.info("Initializing SynthesizerAgent")

        super().__init__()

        self.model = MODELS['claude-4-strands']
        self.agent_name = "synthesizer"

        # Allow environment variable to override default system prompt
        default_prompt = """
        You are a market surveillance data synthesizer that consolidates specialist analysis into objective assessments.

        SYNTHESIS PROTOCOL:
        - Consolidate specialist analyst findings into structured, factual summaries
        - Present information using neutral, descriptive language without emotional indicators
        - Base all statements on data and evidence provided by specialist analysts

        CONTENT REQUIREMENTS:
        - Extract key findings from specialist analysis and present as structured bullet points
        - Include specific metrics, timestamps, and quantitative data where available
        - Note any analytical limitations or data quality considerations
        - Acknowledge conflicting specialist views without taking sides

        LANGUAGE STANDARDS:
        - Use factual, descriptive terminology (e.g., "analysis indicates" rather than "clearly shows")
        - Avoid superlatives, emotional language, or value-laden terms
        - Present observations neutrally (e.g., "trading volume increased by X%" rather than "volume exploded")
        - Use conditional language when appropriate (e.g., "appears to indicate," "suggests")

        OUTPUT FORMAT:
        - Structure response as bullet points addressing the user's specific question
        - Lead with factual observations before analytical conclusions
        - Reference data sources and timeframes for all significant findings
        - Maintain consistent, professional terminology throughout
        """

        self.system_prompt = os.getenv('SYNTHESIZER_PROMPT', default_prompt)
        self.tools = []
        self.callback_handler = None

        logger.info(f"SynthesizerAgent initialized with model: {self.model}")
        logger.debug(f"Agent configuration - name: {self.agent_name}, tools count: {len(self.tools)}")
        logger.debug(f"Using {'custom' if os.getenv('SYNTHESIZER_PROMPT') else 'default'} system prompt")

    def create_agent(self, messages=None, session_id=None):
        """Create an agent with LLM-driven synthesis capabilities"""
        logger.info(f"Creating SynthesizerAgent with session_id: {session_id}")
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
            logger.info("SynthesizerAgent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create SynthesizerAgent: {e}")
            raise


