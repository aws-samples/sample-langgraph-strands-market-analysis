# Standard library imports
import asyncio
import logging
import uuid
from typing import List

# Third-party imports
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph
from strands import Agent

# Local application imports
from src.utils.llm_utils import safe_log_text

# Setup centralized logging
logger = logging.getLogger(__name__)


async def stream_strands_agent_response(agent, prompt):
    tool_count = 0
    previous_tool_use = None
    streaming_output = []
    logger.info(f"Streaming response for prompt: {safe_log_text(prompt)}")
    try:
        async for event in agent.stream_async(prompt):
            current_tool_use = event.get("current_tool_use", {})
            message = event.get("message", {})
            if "data" in event:
                # safe_log_text = ''.join(c for c in event['data'] if c.isascii())
                # logger.info(f"Streaming data chunk: {safe_log_text}")
                chunk = event["data"]
                streaming_output.append(chunk)
                if chunk:
                    chunk = {'data': chunk}
                    yield f"{chunk}"
                    await asyncio.sleep(0)
            
            if "reasoningText" in event:
                chunk = event["reasoningText"]
                if chunk:
                    chunk = {'reasoningText': chunk}
                    yield f"{chunk}"
                    await asyncio.sleep(0)
            
            if current_tool_use and current_tool_use.get("name"):
                tool_name = current_tool_use.get("name", "Unknown tool")
                if previous_tool_use != current_tool_use:
                    previous_tool_use = current_tool_use
                    tool_count += 1
                    yield f"\n\n 🛠️ Tool #{tool_count}:: {tool_name}\n"
                    await asyncio.sleep(0)
            
            if message:
                if message.get("role") == "assistant" and message.get("content"):
                    content = message["content"]
                    if isinstance(content, list):
                        for item in content:
                            if "toolUse" in item:
                                tool_use = item.get("toolUse")
                                tool_use_id = tool_use.get("toolUseId")
                                tool_name = tool_use.get("name")
                                tool_input = tool_use.get("input")
                                yield f"\n\n 🛠️ Tool Name: {tool_name} (ID: {tool_use_id})\n{tool_input}\n"
                                await asyncio.sleep(0)
        
        # streaming_output = content[0].get('text', '')
        logger.info(f"Final assistant message from agent: {safe_log_text(''.join(streaming_output))}")
    
    except Exception as e:
        yield f"Error: {str(e)}"


async def langgraph_stream_writer(agent: Agent, prompt: str, agent_name: str) -> List[str]:
    """
    Generic function to handle streaming from any Strands agent.
    
    Args:
        agent: The Strands Agent instance
        prompt: The prompt to send to the agent
        agent_name: Name of the agent for streaming identification
    
    Returns:
        List of streaming output strings
    """
    logger.info(f"Get LangGraph stream writer for agent: {agent_name}")
    writer = get_stream_writer()
    
    streaming_output = []
    previous_tool_use = None
    writer({"type": "agent_execution",
            "status": "started",
            "agent": agent_name
            })
    await asyncio.sleep(0)
    # from src.utils.handlers import safe_log_event
    logger.info(f"Streaming response for agent: {agent_name} with prompt: {safe_log_text(prompt)}")
    async for event in agent.stream_async(prompt):
        # safe_log_event(event, agent_name)
        current_tool_use = event.get("current_tool_use", {})
        raw_event = event.get("event",{})
        message = event.get("message", {})
        # Stream text generation events
        if "data" in event:
            # Stream to LangGraph
            writer({"type": "text",
                    "content": event["data"],
                    "agent": agent_name})
            streaming_output.append(event["data"])
            await asyncio.sleep(0)
        
        if "reasoningText" in event:
            # Stream to LangGraph
            writer({"type": "reasoningText",
                    "content": event["reasoningText"],
                    "agent": agent_name})
            await asyncio.sleep(0)
        
        elif current_tool_use and current_tool_use.get("name") and current_tool_use.get("toolUseId"):
            tool_name = current_tool_use.get("name", "Unknown tool")
            tool_use_id = current_tool_use.get("toolUseId")
            if previous_tool_use != current_tool_use:
                previous_tool_use = current_tool_use
                # Stream to LangGraph
                writer({
                    "type": "tool",
                    "name": tool_name,
                    'status': "started",
                    'tool_use_id': tool_use_id,
                    "agent": agent_name
                })
                await asyncio.sleep(0)
        elif raw_event:
            if raw_event.get('messageStop') and raw_event['messageStop']['stopReason'] =='tool_use':
                writer({
                    "type": "tool",
                    "status":"tool_use_end",
                    "name": tool_name,
                    "agent": agent_name
                })
                await asyncio.sleep(0)
        elif message:
            if message.get("role") == "assistant" and message.get("content"):
                content = message["content"]
                if isinstance(content, list):
                    # streaming_output = content[0].get('text', '')
                    for item in content:
                        if "toolUse" in item:
                            tool_use = item.get("toolUse")
                            tool_use_id = tool_use.get("toolUseId")
                            tool_name = tool_use.get("name")
                            tool_input = tool_use.get("input")
                            writer({
                                "type": "tool",
                                "name": tool_name,
                                'status': "tool_input",
                                'tool_use_id': tool_use_id,
                                "text": tool_input,
                                "agent": agent_name
                            })
                            await asyncio.sleep(0)
            elif message.get("role") == "user" and message.get("content"):
                content = message["content"]
                if isinstance(content, list):
                    for item in content:
                        if "toolResult" in item:
                            tool_result = item.get("toolResult")
                            tool_use_id = tool_result.get("toolUseId")
                            status = tool_result.get("status")
                            
                            result_content = tool_result.get("content", [])
                            result = ""
                            if isinstance(result_content, list) and result_content:
                                result = result_content[0].get("text", "")
                            
                            writer({
                                'type': "tool",
                                'name':'tool_result',
                                "tool_use_id": tool_use_id,
                                "status": "tool_result",
                                "text": result,
                                "agent": agent_name
                            })
                            await asyncio.sleep(0)
        else:
            # Unknown event shape — log for audit/debugging but don't forward
            # into the user-visible stream (UI only renders a curated vocabulary).
            logger.debug("unhandled strands event for %s keys=%s",
                         agent_name, sorted(event.keys()))
        
    # End of streaming (outside the for loop)
    writer({"type": "agent_execution",
            "status": "end",
            "agent": agent_name
            })
    await asyncio.sleep(0)
    return "".join(streaming_output)


async def stream_langgraph_response(graph:StateGraph,session_id:str, prompt: str):
    """Stream the response from the existing LangGraph implementation for streamlit frontend app"""
    logger.info(f"Streaming response from  stream_langgraph_response for prompt: {safe_log_text(prompt)}")
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session_id: {session_id}")
    
    config = {"configurable": {"thread_id": session_id}}
    initial_state = {
        "session_id": session_id,
        "query_text": prompt
    }
    tool_count = 0
    try:
        # Use the existing graph with the query
        async for chunk in graph.astream(initial_state,
                                        config=config,
                                        stream_mode="custom"):
            if 'type' in chunk and chunk['type'] == 'text' and 'content' in chunk:
                chunk = {'data': chunk['content']}
                yield f"{chunk}"
                await asyncio.sleep(0)
            elif 'type' in chunk and chunk['type'] == 'reasoningText' and 'content' in chunk:
                chunk = {'reasoningText': chunk['content']}
                yield f"{chunk}"
                await asyncio.sleep(0)
            elif 'type' in chunk and chunk['type'] == 'tool' and chunk['status'] == "started":
                tool_count += 1
                yield f"\n\n🛠️ Tool #{tool_count}: {chunk['name']}\"# \\n\\n 🛠️Tool Input:\""
                await asyncio.sleep(0)
            elif 'type' in chunk and chunk['type'] == 'tool' and chunk['status'] == "tool_input":
                tool_name = chunk.get("name", "Unknown tool")
                tool_input = chunk.get("text", "")
                tool_use_id = chunk.get("tool_use_id", "")
                yield f"\n\n 🛠️ Tool Name: {tool_name} (ID: {tool_use_id})\n{tool_input}\n"
                await asyncio.sleep(0)
            elif 'type' in chunk and chunk['type'] == 'agent_execution':
                yield f"\n\n **{chunk['agent']}: {chunk['status']}** \\n\\n"
                await asyncio.sleep(0)
    except Exception as e:
        logger.error(f"Error running graph: {str(e)}")
        raise
