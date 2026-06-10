from src.utils.constants import current_datetime_readable
from src.utils.file_utils import load_prompt_from_file

# Agent Prompts
SECURITY_MONITOR_AGENT_PROMPT = load_prompt_from_file("agents/security_monitor")
BROKER_MONITOR_AGENT_PROMPT = load_prompt_from_file("agents/broker_monitor")
RISK_MONITOR_AGENT_PROMPT = load_prompt_from_file("agents/risk_monitor")
INTEL_ANALYST_AGENT_PROMPT = load_prompt_from_file("agents/intel_analyst")
ORCHESTRATOR_AGENT_PROMPT = load_prompt_from_file("agents/orchestrator")
