# Standard library imports
import logging
from typing import List, Dict, Any, Optional

# Local application imports
from src.agents import (
    BaseAgent,
    SecurityMonitorAgent,
    BrokerMonitorAgent,
    RiskMonitorAgent,
    IntelAnalystAgent,
    OrchestratorAgent,
    SynthesizerAgent)

# Setup centralized logging
logger = logging.getLogger(__name__)

class AgentFactory:
    """Dynamic agent instantiation with state restoration"""
    SECURITY_MONITOR_NAME = "security_monitor"
    BROKER_MONITOR_NAME = "broker_monitor"
    RISK_MONITOR_NAME = "risk_monitor"
    INTEL_ANALYST_NAME = "intel_analyst"
    ORCHESTRATOR_NAME = "orchestrator"
    SYNTHESIZER_NAME = "synthesizer"

    AGENT_CLASSES = {
        SECURITY_MONITOR_NAME: SecurityMonitorAgent,
        BROKER_MONITOR_NAME: BrokerMonitorAgent,
        RISK_MONITOR_NAME: RiskMonitorAgent,
        INTEL_ANALYST_NAME: IntelAnalystAgent,
        ORCHESTRATOR_NAME: OrchestratorAgent,
        SYNTHESIZER_NAME: SynthesizerAgent
    }

    @staticmethod
    def create_agent(agent_name: str, messages: Optional[List[Dict[str, Any]]] = None, session_id: Optional[str] = None) -> BaseAgent:
        """Factory method to create agents based on name"""
        logger.info(f"AgentFactory creating agent: {agent_name} with session_id: {session_id}")

        if agent_name not in AgentFactory.AGENT_CLASSES:
            logger.error(f"Unknown agent name: {agent_name}. Available agents: {list(AgentFactory.AGENT_CLASSES.keys())}")
            raise ValueError(f"Unknown agent name: {agent_name}")

        agent_class = AgentFactory.AGENT_CLASSES[agent_name]
        logger.debug(f"Using agent class: {agent_class.__name__}")

        try:
            if messages:
                agent = agent_class().create_agent(messages=messages, session_id=session_id)
                logger.info(f"Restored {agent_class.__name__} with {len(messages)} messages and session_id: {session_id}")
            else:
                agent = agent_class().create_agent(session_id=session_id)
                logger.info(f"Created fresh {agent_class.__name__} with session_id: {session_id}")

            logger.debug(f"AgentFactory successfully created {agent_class.__name__}")
            return agent
        except Exception as e:
            logger.error(f"Failed to create {agent_class.__name__}: {e}")
            raise
