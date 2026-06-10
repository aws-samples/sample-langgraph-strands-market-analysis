import json
import logging
from typing import Any, Dict, List, Optional

from strands import tool

from src.utils.file_utils import load_agent_reports, load_json_report_definition
from src.tools.mock_data import query_market_data

logger = logging.getLogger(__name__)


@tool
def get_report_list(agent_name: str) -> str:
    """Load the list of available reports for an agent.

    Args:
        agent_name: Name of the agent (e.g. 'security_monitor').

    Returns:
        str: JSON array of reports with name and description.
    """
    logger.info(f"get_report_list called with agent_name: {agent_name}")
    reports_data = load_agent_reports(agent_name)
    return json.dumps(reports_data['reports'], indent=2)


@tool
def get_report_schema(report_name: str, query_intent: str) -> str:
    """Load column and parameter definitions for a report.

    Args:
        report_name: Name of the report (e.g. 'TradeActivity').
        query_intent: What the agent plans to do with the data.

    Returns:
        str: JSON object with reportName, parameters, and columns.
    """
    logger.info(f"get_report_schema called with report_name: {report_name}")
    return json.dumps(load_json_report_definition(report_name), indent=2)


@tool
def run_report(
    report_name: str,
    filters: Dict[str, Any],
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run a predefined report. The tool validates every filter against the
    report's schema and builds a parameterised SQL query. The LLM never writes
    raw SQL, so filter values cannot be injected into the query.

    Args:
        report_name: A report from `get_report_list` (e.g. 'TradeActivity').
        filters: Equality filters keyed by column name, e.g.
                 {"symbol": "AAPL", "date": "2024-03-15"}.
        limit: Optional row cap (1..10000).

    Returns:
        dict: {'success': bool, 'data': str (CSV), 'error': str or None}
    """
    logger.info(f"run_report called: report={report_name} filters={filters} limit={limit}")

    schema = load_json_report_definition(report_name)
    allowed_columns = {c["name"] for c in schema["columns"]}

    # Reject any filter field that is not in the report's column allowlist.
    unknown = set(filters) - allowed_columns
    if unknown:
        raise ValueError(
            f"Unknown filter field(s) {sorted(unknown)} for {report_name}. "
            f"Allowed: {sorted(allowed_columns)}"
        )

    # Build SQL with named bind parameters. Values are NOT interpolated.
    where = " AND ".join(f"{field} = :{field}" for field in filters)
    sql = f"SELECT * FROM {schema['reportName']}"
    if where:
        sql += f" WHERE {where}"

    if limit is not None:
        if not isinstance(limit, int) or not 1 <= limit <= 10_000:
            raise ValueError("limit must be an integer in [1, 10000]")
        sql += f" LIMIT {limit}"

    logger.info(f"run_report sql={sql!r} bind={filters}")

    # In production, pass (sql, filters) to your DB driver's parameterised
    # execute call (e.g. SQLAlchemy text().bindparams, psycopg, Athena
    # ExecutionParameters). Here we hand both to the mock data layer.
    return query_market_data(report_name=report_name, sql=sql, bind=filters)


@tool
def data_analytics(csv_data: str, query: str) -> str:
    """Run SQL queries on CSV data using pandas for advanced analytics.

    Takes CSV data returned by `run_report`, loads it into a pandas DataFrame,
    and executes SQL using pandasql. Reference the DataFrame as 'df'.

    Args:
        csv_data: Raw CSV data as a string.
        query: SQL query to execute on the DataFrame (refer to it as 'df').

    Returns:
        str: Query results as a CSV string.
    """
    import io

    import pandas as pd
    from pandasql import sqldf

    logger.info(f"data_analytics called with query: {query}")
    try:
        df = pd.read_csv(io.StringIO(csv_data))
        logger.info(f"Created DataFrame with shape: {df.shape}")
        result_df = sqldf(query, {"df": df})
        logger.info(f"Query executed, result shape: {result_df.shape}")
        return result_df.to_csv(index=False)
    except Exception as e:
        logger.error(f"Error in data_analytics: {e}")
        raise ValueError(f"Failed to perform data analytics: {e}")
