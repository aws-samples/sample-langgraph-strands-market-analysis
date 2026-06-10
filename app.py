import streamlit as st
import json
import re
import time
import uuid
import boto3
import sys
import os
from streamlit.runtime.scriptrunner import get_script_run_ctx

from src.config.config_manager import ConfigManager

st.set_page_config(page_title="Market Surveillance AI", layout="wide")

# Add this after the title to contain the width
with st.container():
    col1, col2, col3 = st.columns([1, 6, 1])  # Creates padding on sides
    with col2:
        st.title("🔍 Market Surveillance AI")


def get_streamlit_session_id():
    """Get session ID for agent workflow"""
    try:
        ctx = get_script_run_ctx()
        if ctx is None:
            return "streamlit_session_unknown"
        return f"streamlit_{ctx.session_id}"
    except:
        return "streamlit_session_fallback"


# Initialize session_id in session state
if "custom_session_id" not in st.session_state:
    st.session_state.custom_session_id = get_streamlit_session_id()


def render_content_blocks(content: str) -> None:
    """Parse and render content blocks"""
    
    # Split content by code blocks to handle them separately
    parts = re.split(r'(```[\s\S]*?```)', content)
    
    for part in parts:
        if part.startswith('```') and part.endswith('```'):
            # This is a code block
            render_code_block(part)
        elif part.strip():
            # This is regular text/markdown
            st.markdown(part)


def render_code_block(block: str) -> None:
    """Render a code block based on its type"""
    
    # Extract language and content
    lines = block.strip().split('\n')
    first_line = lines[0].strip('`').strip()
    content_lines = lines[1:-1] if len(lines) > 2 else []
    content = '\n'.join(content_lines)
    
    if first_line.lower() == 'json':
        # JSON block
        try:
            json_data = json.loads(content)
            render_json_nicely(json_data)
        except json.JSONDecodeError:
            st.code(content, language='json')
    elif first_line.lower() == 'sql':
        # SQL block - format for better readability
        formatted_sql = format_sql_for_display(content)
        st.code(formatted_sql, language='sql')
    
    elif first_line.lower() == 'csv':
        # CSV block
        render_csv_as_table(content)
    
    else:
        # Unknown code block
        language = first_line.lower() if first_line else None
        st.code(content, language=language)


def render_json_nicely(data: dict) -> None:
    """Render JSON with special handling for key sections"""
    
    # Special sections that need custom rendering
    special_sections = {
        'objective': '🎯 **Objective**',
        'business_insights': '💡 **Business Insights**',
        'data_requirement': '📊 **Data Requirement**',
        'query_data': '📋 **Query Results**',
        'sql_query': '🔍 **SQL Query**'
    }
    
    for key, value in data.items():
        if key in special_sections:
            st.markdown(f"### {special_sections[key]}")
            
            if key == 'business_insights':
                # Render as markdown
                st.markdown(value)
            elif key == 'query_data' and isinstance(value, list) and value:
                # Try to render as table
                render_data_as_table(value)
            
            elif key == 'sql_query':
                # Render SQL with formatting
                if isinstance(value, list):
                    for query in value:
                        formatted_sql = format_sql_for_display(query)
                        st.code(formatted_sql, language='sql')
                else:
                    formatted_sql = format_sql_for_display(value)
                    st.code(formatted_sql, language='sql')
            
            elif isinstance(value, (dict, list)):
                # Complex data as JSON
                st.json(value)
            else:
                # Simple text
                st.write(value)
        else:
            # Regular JSON field
            st.markdown(f"**{key.replace('_', ' ').title()}:**")
            if isinstance(value, (dict, list)):
                st.json(value)
            else:
                st.write(value)


def render_data_as_table(data_list: list) -> None:
    """Render data list as a table if possible"""
    try:
        # Handle multiple CSV datasets
        csv_count = 0
        for idx, data_item in enumerate(data_list):
            if isinstance(data_item, str) and '\n' in data_item:
                # CSV-like string
                csv_count += 1
                if len(data_list) > 1:
                    st.markdown(f"**Dataset {idx + 1}:**")
                render_csv_as_table(data_item)
                if idx < len(data_list) - 1:  # Add spacing between datasets
                    st.markdown("---")
            else:
                # Other format, show as code
                if len(data_list) > 1:
                    st.markdown(f"**Dataset {idx + 1}:**")
                st.code(str(data_item))
                if idx < len(data_list) - 1:  # Add spacing between datasets
                    st.markdown("---")
        
        # If no CSV-like data was found, show all as code
        if csv_count == 0 and len(data_list) == 1:
            st.code(str(data_list[0]))
    
    except Exception as e:
        st.code(str(data_list))
        st.error(f"Error rendering data: {str(e)}")


def render_csv_as_table(csv_content: str) -> None:
    """Convert CSV string to DataFrame and display"""
    try:
        lines = csv_content.strip().split('\n')
        if len(lines) > 1:
            headers = [h.strip() for h in lines[0].split(',')]
            rows = []
            for line in lines[1:]:
                if line.strip():
                    row = [cell.strip() for cell in line.split(',')]
                    rows.append(row)
            
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=headers)
                st.dataframe(df, use_container_width=True)
            else:
                st.code(csv_content)
        else:
            st.code(csv_content)
    except:
        st.code(csv_content)


def format_sql_for_display(sql_query: str) -> str:
    """Format SQL query for better readability with proper line breaks"""
    if not sql_query or not isinstance(sql_query, str):
        return str(sql_query)
    
    # Remove extra whitespace and normalize
    sql = ' '.join(sql_query.split())
    
    # SQL keywords that should start new lines
    line_break_keywords = [
        'SELECT', 'FROM', 'WHERE', 'ORDER BY', 'GROUP BY', 'HAVING',
        'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN',
        'INSERT INTO', 'UPDATE', 'DELETE FROM', 'CREATE TABLE', 'ALTER TABLE',
        'UNION', 'UNION ALL', 'WITH', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'DO', 'BEGIN', 'PERFORM', 'END'
    ]
    
    # Add line breaks before major keywords
    for keyword in line_break_keywords:
        # Case insensitive replacement with line break
        pattern = r'\b' + re.escape(keyword) + r'\b'
        sql = re.sub(pattern, f'\n{keyword}', sql, flags=re.IGNORECASE)
    
    # Special handling for function calls like PERFORM
    sql = re.sub(r'\bDPERFORM\b', '\n    PERFORM', sql, flags=re.IGNORECASE)
    
    # Add proper indentation
    lines = sql.split('\n')
    formatted_lines = []
    indent_level = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Decrease indent for END, closing parentheses
        if line.upper().startswith('END') or line.startswith(')'):
            indent_level = max(0, indent_level - 1)
        
        # Add indentation
        formatted_line = '    ' * indent_level + line
        formatted_lines.append(formatted_line)
        
        # Increase indent after certain keywords
        if (line.upper().startswith(('BEGIN', 'DO', 'CASE', '(')) or
            'BEGIN' in line.upper()):
            indent_level += 1
    
    # Clean up and return
    formatted_sql = '\n'.join(formatted_lines)
    
    # Remove leading newline if present
    formatted_sql = formatted_sql.lstrip('\n')
    
    return formatted_sql


def invoke_agentcore_workflow(prompt: str, session_id: str, runtime_arn: str, region: str = "us-east-1"):
    """Invoke AgentCore workflow via boto3 and yield streaming chunks"""
    
    try:
        print(f"\n{'='*80}")
        print(f"[DEBUG] Creating bedrock-agentcore client for region: {region}")
        agentcore_client = boto3.client("bedrock-agentcore", region_name=region)
        
        print(f"[DEBUG] Invoking runtime ARN: {runtime_arn}")
        print(f"[DEBUG] Session ID: {session_id}")
        print(f"[DEBUG] Prompt: {prompt[:100]}...")
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({"prompt": prompt, "session_id": session_id})
        )
        
        print(f"[DEBUG] Response received. Content type: {response.get('contentType', 'N/A')}")
        print(f"[DEBUG] Response keys: {list(response.keys())}")
        
        # Handle streaming response
        if "text/event-stream" in response.get("contentType", ""):
            print("[DEBUG] Processing text/event-stream response")
            chunk_count = 0
            for line in response["response"].iter_lines(chunk_size=1):
                if line:
                    line = line.decode("utf-8")
                    print(f"[DEBUG] Raw line: {line[:200]}")
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        print(f"[DEBUG] Data string: {data_str[:200]}")
                        try:
                            data = json.loads(data_str)
                            chunk_count += 1
                            print(f"[DEBUG] Chunk #{chunk_count}: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                            
                            # Handle double-wrapped SSE format: the data is a string containing "data: {...}"
                            if isinstance(data, str) and data.startswith("data: "):
                                # Strip outer "data: " and parse inner JSON
                                inner_str = data[6:].strip()  # Remove "data: "
                                print(f"[DEBUG] Found nested SSE, parsing inner: {inner_str[:100]}")
                                try:
                                    inner_data = json.loads(inner_str)
                                    if isinstance(inner_data, dict) and inner_data.get('type') == 'text' and 'content' in inner_data:
                                        print(f"[DEBUG] Yielding nested text content: {inner_data['content'][:50]}")
                                        yield inner_data['content']
                                except json.JSONDecodeError as e:
                                    print(f"[DEBUG] Failed to parse inner JSON: {e}")
                            # Extract text content from SSE format
                            elif isinstance(data, dict):
                                if data.get('type') == 'text' and 'content' in data:
                                    print(f"[DEBUG] Yielding text content: {data['content'][:100]}")
                                    yield data['content']
                                elif 'role' in data and 'content' in data:
                                    content = data['content']
                                    if isinstance(content, list) and len(content) > 0:
                                        if isinstance(content[0], dict) and 'text' in content[0]:
                                            yield content[0]['text']
                                        else:
                                            yield str(content[0])
                                    else:
                                        yield str(content)
                                elif 'text' in data:
                                    yield data['text']
                        except json.JSONDecodeError:
                            # If not JSON, yield as-is
                            if data_str.strip():
                                yield data_str
        else:
            # Handle non-streaming response
            response_obj = response.get("response")
            if hasattr(response_obj, "read"):
                content = response_obj.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                try:
                    response_data = json.loads(content)
                    if isinstance(response_data, dict):
                        if "role" in response_data and "content" in response_data:
                            content_list = response_data["content"]
                            if isinstance(content_list, list) and len(content_list) > 0:
                                if isinstance(content_list[0], dict) and "text" in content_list[0]:
                                    yield content_list[0]["text"]
                                else:
                                    yield str(content_list[0])
                            else:
                                yield str(content_list)
                        else:
                            yield str(response_data)
                    else:
                        yield str(response_data)
                except json.JSONDecodeError:
                    yield content
            else:
                yield str(response_obj)
                
    except Exception as e:
        yield f"Error invoking AgentCore: {str(e)}"


# Main UI

# Initialize session state
if "workflow_messages" not in st.session_state:
    st.session_state.workflow_messages = []

# Load configuration
try:
    config_manager = ConfigManager()
    runtime_arn = config_manager.get_runtime_arn()
    static_config = config_manager.get_static_config()
    region = static_config.get('aws', {}).get('region', 'us-east-1')
except Exception as e:
    st.error(f"Configuration error: {str(e)}")
    st.info("Please run deployment/deploy.sh to deploy the workflow to AgentCore")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("🎛️ Controls")
    
    # Show runtime info
    if runtime_arn:
        st.success("✅ AgentCore Runtime Connected")
        with st.expander("Runtime Details"):
            st.code(runtime_arn)
            st.caption(f"Region: {region}")
    else:
        st.error("❌ No Runtime ARN Found")
        st.info("Run: cd deployment && ./deploy.sh")
    
    # Show message count
    current_msg_count = len(st.session_state.workflow_messages)
    st.markdown(f"Messages: {current_msg_count}")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.workflow_messages = []
        st.rerun()
    
    # Session ID input
    new_session_id = st.text_input(
        "Session ID:",
        value=st.session_state.custom_session_id,
        key="session_id_input"
    )
    if new_session_id != st.session_state.custom_session_id:
        st.session_state.custom_session_id = new_session_id
        st.rerun()

# Use the custom session ID
session_id = st.session_state.custom_session_id

# Show info
st.info("⚙️ **Workflow Orchestrator Agent** - Multi-agent market surveillance powered by AWS AgentCore")

# Display chat history
for message in st.session_state.workflow_messages:
    with st.chat_message(message["role"]):
        render_content_blocks(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about market surveillance..."):
    if not runtime_arn:
        st.error("No runtime ARN configured. Please deploy the workflow first.")
        st.stop()
    
    # Add user message
    st.session_state.workflow_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Stream assistant response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        buffer = []
        
        try:
            # Stream from AgentCore
            for chunk in invoke_agentcore_workflow(prompt, session_id, runtime_arn, region):
                if chunk:
                    buffer.append(chunk)
                    # Update display with cursor
                    current_content = ''.join(buffer)
                    with response_placeholder.container():
                        render_content_blocks(current_content + " |")
            
            # Final render without cursor
            final_content = ''.join(buffer)
            with response_placeholder.container():
                render_content_blocks(final_content)
        
        except Exception as e:
            final_content = f"Connection error: {str(e)}"
            response_placeholder.error(final_content)
        
        # Add to chat history
        st.session_state.workflow_messages.append({"role": "assistant", "content": final_content})