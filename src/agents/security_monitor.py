import logging
from strands import Agent
from src.agents.base_agent import BaseAgent
from src.prompts.system_prompts import SECURITY_MONITOR_AGENT_PROMPT
from src.tools.extraction_tools import get_report_list, get_report_schema, run_report
from src.utils.llm_utils import MODELS

logger = logging.getLogger(__name__)


class SecurityMonitorAgent(BaseAgent):
    """Analyses single-security intraday trading activity for anomalies.

    Has access to: TradeActivity, PriceBars, OrderBook, VolumeProfile reports.
    Detects wash trades, spoofing, and front-running patterns for a single symbol
    within a narrow time window.
    """

    def __init__(self):
        logger.info("Initializing SecurityMonitorAgent")
        super().__init__()
        self.model = MODELS['claude-4-interleaved-strands']
        self.agent_name = "security_monitor"
        self.system_prompt = SECURITY_MONITOR_AGENT_PROMPT
        self.tools = [get_report_list, get_report_schema, run_report]
        self.callback_handler = None
        logger.info(f"SecurityMonitorAgent initialized with model: {self.model}")

    def create_agent(self, messages=None, session_id=None):
        logger.info(f"Creating SecurityMonitorAgent with session_id: {session_id}")
        trace_attributes = None
        if session_id:
            trace_attributes = {"session_id": session_id, "agent_name": self.agent_name}
        try:
            agent = Agent(
                model=self.model, messages=messages, name=self.agent_name,
                system_prompt=self.system_prompt, tools=self.tools,
                callback_handler=self.callback_handler, trace_attributes=trace_attributes
            )
            logger.info("SecurityMonitorAgent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create SecurityMonitorAgent: {e}")
            raise
