import logging
from strands import Agent
from src.agents.base_agent import BaseAgent
from src.prompts.system_prompts import BROKER_MONITOR_AGENT_PROMPT
from src.tools.extraction_tools import get_report_list, get_report_schema, run_report
from src.utils.llm_utils import MODELS

logger = logging.getLogger(__name__)


class BrokerMonitorAgent(BaseAgent):
    """Tracks multi-day broker activity trends and risk scores.

    Has access to: PriceBars, DailySnapshot, RiskScores reports.
    Identifies brokers with abnormal trading patterns or elevated risk scores
    across extended time windows.
    """

    def __init__(self):
        logger.info("Initializing BrokerMonitorAgent")
        super().__init__()
        self.model = MODELS['claude-4-interleaved-strands']
        self.agent_name = "broker_monitor"
        self.system_prompt = BROKER_MONITOR_AGENT_PROMPT
        self.tools = [get_report_list, get_report_schema, run_report]
        self.callback_handler = None
        logger.info(f"BrokerMonitorAgent initialized with model: {self.model}")

    def create_agent(self, messages=None, session_id=None):
        logger.info(f"Creating BrokerMonitorAgent with session_id: {session_id}")
        trace_attributes = None
        if session_id:
            trace_attributes = {"session_id": session_id, "agent_name": self.agent_name}
        try:
            agent = Agent(
                model=self.model, messages=messages, name=self.agent_name,
                system_prompt=self.system_prompt, tools=self.tools,
                callback_handler=self.callback_handler, trace_attributes=trace_attributes
            )
            logger.info("BrokerMonitorAgent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create BrokerMonitorAgent: {e}")
            raise
