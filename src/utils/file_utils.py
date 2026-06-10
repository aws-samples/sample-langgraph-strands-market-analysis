# Standard library imports
import json
import logging
import os

# Setup centralized logging
logger = logging.getLogger(__name__)


def load_agent_reports(agent_name: str) -> dict:
    """Load agent-specific reports JSON file"""
    # Construct the agent-specific reports file path
    reports_filename = f"{agent_name}.json"
    report_desc_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data_catalog", "agent_report_access",
        reports_filename
    )
    
    logger.info(f"Looking for file: {report_desc_path}")
    
    # Check if the agent-specific file exists
    if not os.path.exists(report_desc_path):
        raise FileNotFoundError(f"Reports file not found: {reports_filename} in src/data_catalog/")
    
    # Load the agent-specific report descriptions
    with open(report_desc_path, 'r', encoding='utf-8') as file:
        reports_data = json.load(file)
    
    logger.info(f"Loaded {len(reports_data.get('reports', []))} reports")
    return reports_data


def load_json_report_definition(report_name: str):
    """Load JSON report definition file"""
    json_file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data_catalog", "report_schema_json",
        f"{report_name}.json"
    )
    
    logger.info(f"Looking for template file: {json_file_path}")
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON report template not found for: {report_name}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in report definition: {e}")
        raise ValueError(f"Invalid JSON in report definition: {e}")
    except Exception as e:
        logger.error(f"Error loading report definition: {e}")
        raise ValueError(f"Failed to read report definition file: {e}")


def load_prompt_from_file(prompt_file_name: str) -> str:
    """Load prompt from a text file"""
    prompt_file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data_catalog', 'prompts',
        f"{prompt_file_name}.txt"
    )
    
    if not os.path.exists(prompt_file_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_file_name}")
    
    with open(prompt_file_path, 'r', encoding='utf-8') as file:
        prompt_content = file.read()
    
    return prompt_content


def validate_file_exists(file_path: str) -> bool:
    """Check if file exists with proper error handling"""
    return os.path.exists(file_path) and os.path.isfile(file_path)
