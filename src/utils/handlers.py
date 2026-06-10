# Standard library imports
import json
import logging
from typing import Any

# Setup centralized logging
logger = logging.getLogger(__name__)


def safe_log_event(event, agent_name="TEST"):
    """Safely log event for debugging - handles icons and complex objects"""
    try:
        # Convert to JSON string to handle complex objects
        event_json = json.dumps(event, default=str, ensure_ascii=True, indent=2)
        
        # Remove or replace problematic characters
        safe_event = event_json.encode('ascii', errors='ignore').decode('ascii')
        
        # Truncate if too long (adjust length as needed)
        if len(safe_event) > 2000:
            safe_event = safe_event[:2000] + "\n... [TRUNCATED]"
        
        logger.info(f"{agent_name} EVENT:{safe_event}")
    
    except Exception as e:
        logger.warning(f"{agent_name} Event logging failed: {str(e)}")
        # Fallback - log just the type and keys
        try:
            event_info = {
                "event_type": type(event).__name__,
                "keys": list(event.keys()) if isinstance(event, dict) else "Not a dict"
            }
            logger.info(f"{agent_name} Event (fallback): {event_info}")
        except:
            logger.info(f"{agent_name} Event: Unable to log safely")


def message_buffer_handler(**kwargs):
    if "message" in kwargs and kwargs["message"].get("role") == "assistant":
        logger.debug(json.dumps(kwargs["message"], indent=2))


def debugger_callback_handler(**kwargs):
    # Log the values in kwargs so that we can see everything
    safe_log_event(kwargs)
    logger.debug(kwargs)


class CustomCallbackHandler:
    """Handler for streaming text output and tool invocations to stdout."""
    
    def __init__(self) -> None:
        """Initialize handler."""
        self.tool_count = 0
        self.previous_tool_use = None
    
    def __call__(self, **kwargs: Any) -> None:
        """Stream text output and tool invocations to stdout.
        
        Args:
            **kwargs: Callback event data including:
                - current_tool_use (dict): Information about the current tool being used.
        """
        current_tool_use = kwargs.get("current_tool_use", {})
        
        # Track event loop lifecycle
        if kwargs.get("init_event_loop", False):
            logger.debug("\n🔄 Event loop initialized")
        elif kwargs.get("start_event_loop", False):
            logger.debug("\n▶️ Event loop cycle starting")
        elif kwargs.get("start", False):
            logger.debug("\n🔄 New cycle started")
        elif "message" in kwargs:
            logger.debug(f"\n💬 New message created: {json.dumps(kwargs['message'], indent=2)}")
        elif kwargs.get("complete", False):
            logger.debug("\n✅ Cycle completed")
        elif kwargs.get("force_stop", False):
            logger.warning(f"🛑 Event loop force-stopped: {kwargs.get('force_stop_reason', 'unknown reason')}")
        
        if current_tool_use and current_tool_use.get("name"):
            tool_name = current_tool_use.get("name", "Unknown tool")
            if self.previous_tool_use != current_tool_use:
                self.previous_tool_use = current_tool_use
                self.tool_count += 1
                logger.debug(f"\n🔧 Using tool #{self.tool_count}: {tool_name}")
