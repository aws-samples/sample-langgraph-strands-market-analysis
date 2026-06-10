# Standard library imports
import asyncio
import json
import logging
from typing import List, Dict, Any, TypedDict, Optional

# Third-party imports
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Local application imports
from src.agents.agent_factory import AgentFactory
from src.utils.constants import current_datetime_readable
from src.utils.llm_utils import parse_agent_json_response, safe_log_text
from src.utils.session_manager import SessionManager
from src.utils.stream import langgraph_stream_writer


logger = logging.getLogger(__name__)


# Define the state schema for our agents
class AgentState(TypedDict):
    query_text: str
    session_id: Optional[str]  # Add session_id to state
    # Orchestration specific state
    agent_task_map: Optional[Dict[str, str]]
    required_agents: Optional[List[str]]
    orchestrator_context: Optional[Dict[str, Any]]
    # Strands Agent State for Dynamic Creation
    orchestrator_state: Optional[Dict[str, Any]]
    security_monitor_state: Optional[Dict[str, Any]]
    broker_monitor_state: Optional[Dict[str, Any]]
    risk_monitor_state: Optional[Dict[str, Any]]
    intel_analyst_state: Optional[Dict[str, Any]]
    synthesizer_state: Optional[Dict[str, Any]]
    # Insights from each agent
    security_monitor_insights: Optional[Dict[str, Any]]
    broker_monitor_insights: Optional[Dict[str, Any]]
    risk_monitor_insights: Optional[Dict[str, Any]]
    intel_analyst_insights: Optional[Dict[str, Any]]
    synthesizer_insights: Optional[str]
    # final_response: Optional[List[str]]
    current_agent_index: Optional[int]


class Workflow:
    """Factory to create session-scoped workflows with isolated agent instances"""

    def __init__(self):
        # Initialize session management
        self.session_manager = SessionManager()
        self.checkpointer = MemorySaver()
        self.graph = self._create_workflow()

    def build_orchestrator_context(self, state: AgentState) -> str:
        """
        Build context string for orchestrator based on previous workflow execution results.
        """
        prev_context = None

        if state.get("orchestrator_context"):
            prev_context = state["orchestrator_context"]
            logger.info(f"Building orchestrator context from previous execution: {safe_log_text(prev_context)}")

            return f"""FOLLOWING IS FINAL RESULT FROM YOUR PREVIOUS ORCHESTRATION.
USE THE CONTEXT TO PROCESS THE CURRENT QUERY.
PREVIOUS EXECUTION CONTEXT: {prev_context}"""

        return ""

    def get_agent_instance(self, state: AgentState, agent_state_name: str, agent_name: str):
        """
        Get or create an agent instance based on the current state.
        """
        session_id = state.get("session_id")

        if state.get(agent_state_name) and state[agent_state_name].get("messages"):
            logger.info(f"Restoring {agent_state_name} with previous messages and session_id: {session_id}")
            messages = state[agent_state_name]["messages"]
            agent = AgentFactory.create_agent(
                agent_name=agent_name,
                messages=messages,
                session_id=session_id
            )
        else:
            logger.info(f"Creating fresh {agent_name} instance with session_id: {session_id}")
            agent = AgentFactory.create_agent(agent_name=agent_name, session_id=session_id)

        return agent

    async def orchestrator(self, state: AgentState) -> AgentState:
        """
        Orchestrator analyzes the query and determines which specialist agents are needed.
        """
        logger.info(f"Orchestrator processing query: {state['query_text']}")
        logger.info("Build context from previous execution")
        previous_context = None
        if state.get("orchestrator_context"):
            previous_context = self.build_orchestrator_context(state)
            logger.info("Orchestrator using previous execution context")
            prompt = f"""{previous_context}
NEW QUERY: {state['query_text']}
Based on the previous execution context above, determine which agents are needed for this new query.
Avoid redundant analysis if the previous results already address the new query."""
        else:
            prompt = state['query_text']
            logger.info("Orchestrator processing original query without previous context")

        agent = self.get_agent_instance(state=state, agent_state_name="orchestrator_state",
                                        agent_name=AgentFactory.ORCHESTRATOR_NAME)

        logger.info(f"Orchestrator prompt: {safe_log_text(prompt)}")
        logger.info("Inside orchestrator: Stream strands agent response to langgraph stream writer")
        final_response = await langgraph_stream_writer(agent,
                                                        prompt,
                                                        AgentFactory.ORCHESTRATOR_NAME)

        logger.info(f"Orchestrator streaming output: {safe_log_text(final_response)}")

        required_agents = []
        agent_task_map = {}

        try:
            agent_json_output = parse_agent_json_response(final_response)
            agent_tasks = agent_json_output.get("agent_tasks", [])
            if agent_tasks:
                # Create a map of agent names to their tasks
                agent_task_map = {task["agent"]: task["task"] for task in agent_tasks}
                required_agents = [task["agent"] for task in agent_tasks]
        except Exception as e:
            logger.warning(f"No structured task returned from orchestrator agent or error parsing json response: {e}")

        logger.info(f"=====> Required Agents: {required_agents}")
        orchestrator_state = {
            "messages": agent.messages  # Strands agent messages
        }

        # Partial state update — LangGraph merges it into the overall state.
        # We explicitly null previous-run insights so stale data from a prior
        # query in the same session isn't picked up by the synthesiser.
        return {
            "orchestrator_state": orchestrator_state,
            "agent_task_map": agent_task_map,
            "required_agents": required_agents,
            "current_agent_index": 0 if required_agents else None,
            "security_monitor_insights": None,
            "broker_monitor_insights": None,
            "risk_monitor_insights": None,
            "intel_analyst_insights": None,
            "synthesizer_insights": None,
            "orchestrator_context": None,
        }

    async def security_monitor(self, state: AgentState) -> AgentState:
        """
        Performs detailed analysis of specific market events and individual trades
        in narrow time windows.
        """
        logger.info(f"====>{AgentFactory.SECURITY_MONITOR_NAME} performing analysis...")

        agent_task_map = state.get("agent_task_map", {})
        current_task = agent_task_map.get(AgentFactory.SECURITY_MONITOR_NAME)
        prompt = current_task if current_task else state['query_text']

        logger.info(f"Current task for security_monitor: {prompt}")

        agent = self.get_agent_instance(state=state, agent_state_name="security_monitor_state",
                                        agent_name=AgentFactory.SECURITY_MONITOR_NAME)

        logger.info("Inside Security Monitor: Stream strands agent response to langgraph stream writer")
        final_response = await langgraph_stream_writer(agent,
                                                        prompt,
                                                        AgentFactory.SECURITY_MONITOR_NAME)
        logger.info(f"Security Monitor streaming output: {safe_log_text(final_response)}")

        try:
            agent_json_output = parse_agent_json_response(final_response)
            business_insights = agent_json_output.get("business_insights", [])
        except Exception as e:
            logger.warning(f"No structured response from security_monitor agent or error parsing json response: {e}")
            business_insights = f"No explicit insight available, storing raw response {final_response}"

        security_monitor_state = {
            "messages": agent.messages  # Strands agent messages
        }

        return {
            "security_monitor_state": security_monitor_state,
            "security_monitor_insights": {
                "task": current_task,
                "business_insights": business_insights
            },
            "current_agent_index": state.get("current_agent_index", 0) + 1
        }

    async def broker_monitor(self, state: AgentState) -> AgentState:
        """
        Performs detailed analysis of specific market events and individual trades
        for broad time windows.
        """
        logger.info(f"====>{AgentFactory.BROKER_MONITOR_NAME} performing analysis...")

        agent_task_map = state.get("agent_task_map", {})
        current_task = agent_task_map.get(AgentFactory.BROKER_MONITOR_NAME)
        prompt = current_task if current_task else state['query_text']

        logger.info(f"Current task for broker_monitor: {prompt}")

        agent = self.get_agent_instance(state=state, agent_state_name="broker_monitor_state",
                                        agent_name=AgentFactory.BROKER_MONITOR_NAME)

        logger.info("Inside Broker Monitor: Stream strands agent response to langgraph stream writer")
        final_response = await langgraph_stream_writer(agent,
                                                        prompt,
                                                        AgentFactory.BROKER_MONITOR_NAME)
        logger.info(f"Broker Monitor streaming output: {safe_log_text(final_response)}")

        try:
            agent_json_output = parse_agent_json_response(final_response)
            business_insights = agent_json_output.get("business_insights", [])
        except Exception as e:
            logger.warning(f"No structured response from broker_monitor agent or error parsing json response: {e}")
            business_insights = f"No explicit insight available, storing raw response {final_response}"

        broker_monitor_state = {
            "messages": agent.messages  # Strands agent messages
        }

        return {
            "broker_monitor_state": broker_monitor_state,
            "broker_monitor_insights": {
                "task": current_task,
                "business_insights": business_insights
            },
            "current_agent_index": state.get("current_agent_index", 0) + 1
        }

    async def risk_monitor(self, state: AgentState) -> AgentState:
        """
        Analyzes patterns and events over a prolonged time period.
        """
        logger.info(f"====>{AgentFactory.RISK_MONITOR_NAME} performing analysis...")

        agent_task_map = state.get("agent_task_map", {})
        current_task = agent_task_map.get(AgentFactory.RISK_MONITOR_NAME)
        prompt = current_task if current_task else state['query_text']

        logger.info(f"Current task for risk_monitor: {prompt}")
        agent = self.get_agent_instance(state=state, agent_state_name="risk_monitor_state",
                                        agent_name=AgentFactory.RISK_MONITOR_NAME)

        logger.info("Inside Risk Monitor: Stream strands agent response to langgraph stream writer")
        final_response = await langgraph_stream_writer(agent,
                                                        prompt,
                                                        AgentFactory.RISK_MONITOR_NAME)
        logger.info(f"Risk Monitor streaming output: {safe_log_text(final_response)}")
        try:
            agent_json_output = parse_agent_json_response(final_response)
            business_insights = agent_json_output.get("business_insights", [])
        except Exception as e:
            logger.warning(f"No structured response from risk_monitor agent or error parsing json response: {e}")
            business_insights = f"No explicit insight available, storing raw response {final_response}"

        risk_monitor_state = {
            "messages": agent.messages  # Strands agent messages
        }

        return {
            "risk_monitor_state": risk_monitor_state,
            "risk_monitor_insights": {
                "task": current_task,
                "business_insights": business_insights
            },
            "current_agent_index": state.get("current_agent_index", 0) + 1
        }

    async def intel_analyst(self, state: AgentState) -> AgentState:
        """
        Gathers external market intelligence and contextual information via online research.
        """
        logger.info(f"====>{AgentFactory.INTEL_ANALYST_NAME} performing analysis...")

        agent_task_map = state.get("agent_task_map", {})
        current_task = agent_task_map.get(AgentFactory.INTEL_ANALYST_NAME)
        prompt = current_task if current_task else state['query_text']

        logger.info(f"Current task for intel_analyst: {prompt}")
        agent = self.get_agent_instance(state=state, agent_state_name="intel_analyst_state",
                                        agent_name=AgentFactory.INTEL_ANALYST_NAME)

        logger.info("Inside Intel Analyst: Stream strands agent response to langgraph stream writer")
        final_response = await langgraph_stream_writer(agent,
                                                        prompt,
                                                        AgentFactory.INTEL_ANALYST_NAME)
        logger.info(f"Intel Analyst streaming output: {safe_log_text(final_response)}")
        try:
            agent_json_output = parse_agent_json_response(final_response)
            business_insights = agent_json_output.get("business_insights", [])
        except Exception as e:
            logger.warning(f"No structured response from intel_analyst agent or error parsing json response: {e}")
            business_insights = f"No explicit insight available, storing raw response {final_response}"

        intel_analyst_state = {
            "messages": agent.messages  # Strands agent messages
        }

        return {
            "intel_analyst_state": intel_analyst_state,
            "intel_analyst_insights": {
                "task": current_task,
                "business_insights": business_insights
            },
            "current_agent_index": state.get("current_agent_index", 0) + 1
        }

    def build_synthesizer_context(self, state: AgentState) -> str:
        """
        Build context string for synthesizer based on current workflow execution results.
        """
        context_parts = []

        context_parts.append(f"Original query: {state['query_text']}")

        if state.get("security_monitor_insights"):
            context_parts.append(f"SECURITY MONITOR ANALYSIS: {state['security_monitor_insights']}")

        if state.get("risk_monitor_insights"):
            context_parts.append(f"RISK MONITOR ANALYSIS: {state['risk_monitor_insights']}")

        if state.get("intel_analyst_insights"):
            context_parts.append(f"INTEL ANALYST ANALYSIS: {state['intel_analyst_insights']}")

        if state.get("broker_monitor_insights"):
            context_parts.append(f"BROKER MONITOR ANALYSIS: {state['broker_monitor_insights']}")

        return "\n\n".join(context_parts)

    async def synthesizer(self, state: AgentState) -> AgentState:
        """
        Combines insights from all analysts into a comprehensive response.
        """
        logger.info("=====>Synthesizing final response...")

        context = self.build_synthesizer_context(state)
        logger.info(f"Context for synthesizer: {safe_log_text(context)}")

        prompt = f"Synthesize the following analysis results into a comprehensive response:\n\n{context}"

        agent = self.get_agent_instance(state=state, agent_state_name="synthesizer_state",
                                        agent_name=AgentFactory.SYNTHESIZER_NAME)

        logger.info("Inside Synthesizer:Stream strands agent response to langgraph stream writer")
        final_response = await langgraph_stream_writer(agent, prompt, AgentFactory.SYNTHESIZER_NAME)
        logger.info(f"Synthesizer streaming output: {safe_log_text(final_response)}")

        orchestrator_context = {
            "query_text": state['query_text'],
            "required_agents": state.get("required_agents", []),
            "final_result": final_response,
        }

        logger.info(f"Orchestrator context updated with current execution results: {safe_log_text(orchestrator_context)}")

        synthesizer_state = {
            "messages": agent.messages  # Strands agent messages
        }

        return {
            "synthesizer_insights": final_response,
            "orchestrator_context": orchestrator_context,
            "synthesizer_state": synthesizer_state
        }

    def route_analysts(self, state: AgentState) -> str:
        required_agents = state.get("required_agents", [])
        current_index = state.get("current_agent_index", 0)

        if not required_agents:
            return END

        if current_index < len(required_agents):
            return required_agents[current_index]

        return AgentFactory.SYNTHESIZER_NAME

    def _create_workflow(self) -> StateGraph:
        """
        Create the LangGraph workflow with async agents.
        This function sets up the state graph and adds nodes and edges.
        """
        logger.info("Creating LangGraph workflow...")

        # Create the graph
        workflow = StateGraph(AgentState)

        logger.info("Add nodes these are async functions using Strands agents")
        workflow.add_node(AgentFactory.ORCHESTRATOR_NAME, self.orchestrator)
        workflow.add_node(AgentFactory.SECURITY_MONITOR_NAME, self.security_monitor)
        workflow.add_node(AgentFactory.BROKER_MONITOR_NAME, self.broker_monitor)
        workflow.add_node(AgentFactory.RISK_MONITOR_NAME, self.risk_monitor)
        workflow.add_node(AgentFactory.INTEL_ANALYST_NAME, self.intel_analyst)
        workflow.add_node(AgentFactory.SYNTHESIZER_NAME, self.synthesizer)

        logger.info("Add conditional edges from orchestrator and every specialist")
        # Single source of truth for the router's valid destinations. Every
        # node that delegates to route_analysts uses the same map, so the
        # router's return domain is always a subset of what the edges accept.
        specialists = [
            AgentFactory.SECURITY_MONITOR_NAME,
            AgentFactory.BROKER_MONITOR_NAME,
            AgentFactory.RISK_MONITOR_NAME,
            AgentFactory.INTEL_ANALYST_NAME,
        ]
        all_targets = {name: name for name in specialists} | {
            AgentFactory.SYNTHESIZER_NAME: AgentFactory.SYNTHESIZER_NAME,
            END: END,
        }

        workflow.add_conditional_edges(
            AgentFactory.ORCHESTRATOR_NAME, self.route_analysts, all_targets,
        )
        for name in specialists:
            workflow.add_conditional_edges(name, self.route_analysts, all_targets)

        workflow.add_edge(AgentFactory.SYNTHESIZER_NAME, END)

        logger.info("Set entry point for the workflow")
        workflow.set_entry_point(AgentFactory.ORCHESTRATOR_NAME)

        logger.info("Compiling LangGraph workflow...")
        graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("LangGraph workflow compiled successfully.")
        return graph

    async def stream_query(self, session_id: str, prompt: str):
        """Process query for specific session"""
        # Validate session exists, create if not found
        session_info = self.session_manager.get_session_info(session_id)
        if not session_info:
            logger.warning(f"Session ID not found: {session_id}. Creating new session.")
            # Auto-create session for ECS compatibility with SessionManager
            created_session_id = self.session_manager.create_session(
                user_id="auto_created",
                session_name=f"auto_{session_id[:12]}",
                session_id=session_id  # Pass frontend session ID directly
            )
            session_info = self.session_manager.get_session_info(created_session_id)
            logger.info(f"Auto-created session: {created_session_id}")

        # Update session activity
        self.session_manager.update_session_activity(session_id)

        logger.info(f"Inside Workflow: streaming query for session {session_id} (user: {session_info.get('user_id', 'unknown')})"
                    f" with prompt: {safe_log_text(prompt)}")

        config = {
            "configurable": {"thread_id": session_id},
        }

        initial_state = {
            "session_id": session_id,
            "query_text": prompt
        }

        try:
            async for chunk in self.graph.astream(initial_state, config=config, stream_mode="custom"):
                try:
                    # Convert chunk to JSON string for SSE format
                    json_chunk = json.dumps(chunk)
                    yield f"data: {json_chunk}\n\n"
                except (TypeError, ValueError) as e:
                    # If chunk is not JSON serializable, convert to string
                    yield f"data: {str(chunk)}\n\n"
        except Exception as e:
            logger.error(f"Error processing query for session {session_id}: {e}")
            yield f"data: {json.dumps({'error': str(e), 'session_id': session_id})}\n\n"


# Async main function to handle streaming
async def main():
    """Main async function to run the graph with streaming agents"""
    log_file = f'./logs/agent_workflow_{current_datetime_readable}.log'.replace(":", "_").strip()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file)
        ]
    )

    import sys

    # Create a dedicated session manager for this example
    workflow = Workflow()
    session_manager = workflow.session_manager  # Use the workflow's session manager

    async def test_stream(session_id: str, prompt: str):
        logger.info(f"Testing stream for session {session_id} with prompt: {safe_log_text(prompt)}")
        async for chunk in workflow.stream_query(session_id, prompt):
            if chunk.startswith("data: "):
                # Remove the "data: " prefix
                json_str = chunk[6:]  # Remove "data: "
                try:
                    # Parse the JSON data
                    chunk = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON: {e}")
                    raise

            # Handle error responses
            if isinstance(chunk, dict) and 'error' in chunk:
                logger.error(f"Error: {chunk['error']}")
                return

            if 'type' in chunk and chunk['type'] == 'text' and 'content' in chunk:
                print(f"{chunk['content']}", end="", flush=True)
                await asyncio.sleep(0)

            elif 'type' in chunk and chunk['type'] == 'reasoningText' and 'content' in chunk:
                print(f"{chunk['content']}", end="", flush=True)
                await asyncio.sleep(0)

            elif 'type' in chunk and chunk['type'] == 'agent_execution':
                print(f"\n\n **{chunk['agent']}: {chunk['status']}** \n\n")
                await asyncio.sleep(0)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--chat":
            # Create a new session for interactive chat
            session_id = session_manager.create_session(user_id="interactive_user", session_name="chat_session")
            logger.info(f"Started chat session: {session_id}")

            while True:
                try:
                    prompt = input("\nQuery: ").strip()
                    if prompt.lower() in ['quit', 'exit', 'q']:
                        logger.info("Exiting chat mode")
                        logger.info(f"Session info: {session_manager.get_session_info(session_id)}")
                        break
                    if not prompt:
                        continue

                    logger.info(f"Processing query: {prompt}")
                    await test_stream(session_id, prompt)
                except KeyboardInterrupt:
                    logger.info("Chat interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error in chat mode: {e}")
                    logger.error(f"Error: {e}")

        elif sys.argv[1] == "--execute":
            # Create a session for testing context persistence
            session_id = session_manager.create_session(user_id="test_user", session_name="context_test")
            logger.info(f"Testing context persistence with session: {session_id}")

            # First query to create context
            await test_stream(session_id, "What caused the price for AAPL to increase at 11:00 AM on March 15, 2024?")
            logger.info("\n" + "=" * 50)
            # Second query to test context
            await test_stream(session_id, "Which query are you referring to here?")

            logger.info(f"\nSession info: {session_manager.get_session_info(session_id)}")

        elif sys.argv[1] == "--multi-user":
            # Test multiple users with separate sessions
            user1_session = session_manager.create_session(user_id="user_1", session_name="user1_analysis")
            user2_session = session_manager.create_session(user_id="user_2", session_name="user2_analysis")

            logger.info(f"User 1 session: {user1_session}")
            logger.info(f"User 2 session: {user2_session}")

            await test_stream(user1_session, "Analyze stock ABC")
            await test_stream(user2_session, "Analyze participant XYZ")
            await test_stream(user1_session, "What was my previous query?")  # Should reference ABC
            await test_stream(user2_session, "What was my previous query?")  # Should reference XYZ

            # Show session information
            logger.info(f"\nUser 1 sessions: {session_manager.list_sessions('user_1')}")
            logger.info(f"User 2 sessions: {session_manager.list_sessions('user_2')}")
            logger.info(f"All sessions: {session_manager.list_sessions()}")

        elif sys.argv[1] == "--visualize":
            logger.info("Generating workflow visualization...")
            try:
                mermaid_text = workflow.graph.get_graph().draw_mermaid()
                with open("workflow_diagram.mmd", "w") as f:
                    f.write(mermaid_text)
                logger.info("Workflow diagram saved to workflow_diagram.mmd")
            except Exception as e:
                logger.error(f"Error generating mermaid: {e}")

        else:
            logger.info("Usage: python -m workflow [--chat|--execute|--multi-user|--visualize]")
    else:
        logger.info("Usage: python -m workflow [--chat|--execute|--multi-user|--visualize]")


# Example usage
if __name__ == "__main__":
    asyncio.run(main())
