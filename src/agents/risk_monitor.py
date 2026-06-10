import logging
from strands import Agent
from src.agents.base_agent import BaseAgent
from src.prompts.system_prompts import RISK_MONITOR_AGENT_PROMPT
from src.tools.extraction_tools import get_report_list, get_report_schema, run_report
from src.utils.llm_utils import MODELS

logger = logging.getLogger(__name__)


class RiskMonitorAgent(BaseAgent):
    """Monitors single-day broker risk metrics and activity patterns.

    Has access to: TradeActivity, RiskScores, BrokerActivity reports.
    Focuses on identifying high-risk brokers and unusual activity concentrations
    within a single trading session.
    """

    def __init__(self):
        logger.info("Initializing RiskMonitorAgent")
        super().__init__()
        self.model = MODELS['claude-4-interleaved-strands']
        self.agent_name = "risk_monitor"
        self.system_prompt = RISK_MONITOR_AGENT_PROMPT
        self.tools = [get_report_list, get_report_schema, run_report]
        self.callback_handler = None
        logger.info(f"RiskMonitorAgent initialized with model: {self.model}")

    def create_agent(self, messages=None, session_id=None):
        logger.info(f"Creating RiskMonitorAgent with session_id: {session_id}")
        trace_attributes = None
        if session_id:
            trace_attributes = {"session_id": session_id, "agent_name": self.agent_name}
        try:
            agent = Agent(
                model=self.model, messages=messages, name=self.agent_name,
                system_prompt=self.system_prompt, tools=self.tools,
                callback_handler=self.callback_handler, trace_attributes=trace_attributes
            )
            logger.info("RiskMonitorAgent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create RiskMonitorAgent: {e}")
            raise
