import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Mock market data keyed by report name. In production this layer calls a real
# database (RDS/Redshift/Athena). The tool layer passes parameterised SQL +
# bound values, so the DB does the actual filtering.
MOCK_DATA = {
    "TradeActivity": (
        "date,time,symbol,price,volume,side,broker\n"
        "2024-03-15,09:35:00,AAPL,172.50,1500,BUY,ALPHA_CAPITAL\n"
        "2024-03-15,09:35:02,AAPL,172.55,800,BUY,SUMMIT_TRADING\n"
        "2024-03-15,09:36:15,AAPL,172.30,2200,SELL,VERTEX_SECURITIES\n"
        "2024-03-15,09:40:10,MSFT,425.20,3000,BUY,PINNACLE_PARTNERS\n"
        "2024-03-15,09:41:30,MSFT,425.35,1200,SELL,ALPHA_CAPITAL\n"
        "2024-03-15,09:45:00,TSLA,171.10,500,BUY,MERIDIAN_BROKERS\n"
        "2024-03-15,09:47:22,TSLA,170.95,1800,SELL,CRESTVIEW_CAPITAL\n"
        "2024-03-15,10:00:05,AAPL,173.00,2500,BUY,SUMMIT_TRADING\n"
        "2024-03-15,10:05:30,MSFT,425.50,4000,BUY,VERTEX_SECURITIES\n"
        "2024-03-15,10:10:15,TSLA,171.50,900,SELL,ALPHA_CAPITAL\n"
        "2024-03-15,10:15:00,AAPL,173.10,1100,SELL,CRESTVIEW_CAPITAL\n"
        "2024-03-15,10:20:45,MSFT,425.80,2800,BUY,ALPHA_CAPITAL\n"
        "2024-03-15,10:25:30,TSLA,171.80,1600,BUY,SUMMIT_TRADING\n"
        "2024-03-15,10:30:00,AAPL,173.25,3200,BUY,PINNACLE_PARTNERS\n"
        "2024-03-15,10:35:10,MSFT,426.10,1500,SELL,MERIDIAN_BROKERS"
    ),
    "PriceBars": (
        "date,time,symbol,high,low,volume,num_trades,vwap\n"
        "2024-03-15,09:30:00,AAPL,172.80,171.90,15000,45,172.35\n"
        "2024-03-15,10:00:00,AAPL,173.20,172.10,22000,67,172.65\n"
        "2024-03-15,10:30:00,AAPL,173.50,172.80,18000,52,173.15\n"
        "2024-03-15,11:00:00,AAPL,173.80,173.20,14000,41,173.50\n"
        "2024-03-15,09:30:00,MSFT,425.50,424.80,12000,38,425.15\n"
        "2024-03-15,10:00:00,MSFT,426.00,425.20,19000,55,425.60\n"
        "2024-03-15,10:30:00,MSFT,426.30,425.70,16000,48,426.00\n"
        "2024-03-15,09:30:00,TSLA,171.50,170.20,8000,25,170.85\n"
        "2024-03-15,10:00:00,TSLA,172.00,171.00,11000,33,171.50\n"
        "2024-03-15,10:30:00,TSLA,172.30,171.60,9500,29,171.95"
    ),
    "BrokerActivity": (
        "date,broker,symbol,buy_volume,sell_volume,num_trades,market_share_pct\n"
        "2024-03-15,ALPHA_CAPITAL,AAPL,5000,3200,28,18.5\n"
        "2024-03-15,SUMMIT_TRADING,AAPL,4200,2800,22,15.8\n"
        "2024-03-15,VERTEX_SECURITIES,AAPL,3800,4500,25,18.7\n"
        "2024-03-15,PINNACLE_PARTNERS,AAPL,3200,2100,19,12.0\n"
        "2024-03-15,PINNACLE_PARTNERS,MSFT,6000,2100,30,26.1\n"
        "2024-03-15,MERIDIAN_BROKERS,MSFT,2500,3800,18,20.3\n"
        "2024-03-15,ALPHA_CAPITAL,MSFT,4800,3100,25,25.5\n"
        "2024-03-15,CRESTVIEW_CAPITAL,TSLA,1800,2200,12,21.1\n"
        "2024-03-15,ALPHA_CAPITAL,TSLA,3000,1500,15,23.7\n"
        "2024-03-15,SUMMIT_TRADING,TSLA,2200,1900,14,21.6"
    ),
    "RiskScores": (
        "date,symbol,broker,risk_score,anomaly_flag\n"
        "2024-03-15,AAPL,ALPHA_CAPITAL,0.12,0\n"
        "2024-03-15,AAPL,SUMMIT_TRADING,0.08,0\n"
        "2024-03-15,AAPL,VERTEX_SECURITIES,0.45,1\n"
        "2024-03-15,AAPL,PINNACLE_PARTNERS,0.18,0\n"
        "2024-03-15,MSFT,PINNACLE_PARTNERS,0.22,0\n"
        "2024-03-15,MSFT,MERIDIAN_BROKERS,0.67,1\n"
        "2024-03-15,MSFT,ALPHA_CAPITAL,0.14,0\n"
        "2024-03-15,TSLA,CRESTVIEW_CAPITAL,0.15,0\n"
        "2024-03-15,TSLA,ALPHA_CAPITAL,0.31,0\n"
        "2024-03-15,TSLA,SUMMIT_TRADING,0.52,1"
    ),
    "OrderBook": (
        "date,time,symbol,bid_price,bid_size,ask_price,ask_size,spread,depth_imbalance\n"
        "2024-03-15,09:30:00,AAPL,172.40,2500,172.50,1800,0.10,0.16\n"
        "2024-03-15,09:45:00,AAPL,172.55,3200,172.60,2100,0.05,0.21\n"
        "2024-03-15,10:00:00,AAPL,172.90,1800,173.00,2800,0.10,-0.22\n"
        "2024-03-15,10:30:00,AAPL,173.15,2200,173.25,1500,0.10,0.19\n"
        "2024-03-15,09:30:00,MSFT,425.00,1500,425.20,2000,0.20,-0.14\n"
        "2024-03-15,09:45:00,MSFT,425.15,2800,425.25,1200,0.10,0.40\n"
        "2024-03-15,10:00:00,MSFT,425.40,2100,425.55,1900,0.15,0.05\n"
        "2024-03-15,09:30:00,TSLA,170.80,1200,171.10,1800,0.30,-0.20\n"
        "2024-03-15,09:45:00,TSLA,171.00,2000,171.15,1600,0.15,0.11\n"
        "2024-03-15,10:00:00,TSLA,171.40,1500,171.55,2200,0.15,-0.19"
    ),
    "DailySnapshot": (
        "date,symbol,open,close,high,low,total_volume,total_trades,net_change,change_pct\n"
        "2024-03-14,AAPL,171.20,172.10,172.50,170.80,285000,820,0.90,0.53\n"
        "2024-03-15,AAPL,172.30,173.50,173.80,171.90,310000,945,1.40,0.81\n"
        "2024-03-14,MSFT,424.00,425.10,425.80,423.50,195000,580,1.10,0.26\n"
        "2024-03-15,MSFT,425.00,426.20,426.50,424.80,220000,640,1.10,0.26\n"
        "2024-03-14,TSLA,169.50,170.80,171.20,168.90,165000,490,1.30,0.77\n"
        "2024-03-15,TSLA,170.90,172.00,172.30,170.20,175000,520,1.20,0.70"
    ),
    "VolumeProfile": (
        "date,symbol,price_level,volume_at_price,pct_of_total,side_ratio\n"
        "2024-03-15,AAPL,172.00,45000,14.5,0.55\n"
        "2024-03-15,AAPL,172.50,62000,20.0,0.48\n"
        "2024-03-15,AAPL,173.00,85000,27.4,0.62\n"
        "2024-03-15,AAPL,173.50,38000,12.3,0.41\n"
        "2024-03-15,MSFT,425.00,35000,15.9,0.52\n"
        "2024-03-15,MSFT,425.50,52000,23.6,0.58\n"
        "2024-03-15,MSFT,426.00,48000,21.8,0.45\n"
        "2024-03-15,TSLA,171.00,28000,16.0,0.50\n"
        "2024-03-15,TSLA,171.50,42000,24.0,0.63\n"
        "2024-03-15,TSLA,172.00,31000,17.7,0.39"
    ),
}


def query_market_data(report_name: str, sql: str, bind: Dict[str, Any]) -> Dict[str, Any]:
    """Mock executor — stands in for a parameterised DB call.

    In production this function wraps a driver that binds parameters server-side
    (e.g. SQLAlchemy `text(sql).bindparams(**bind)`, psycopg `cur.execute(sql,
    bind)`, or Athena `StartQueryExecution` with `ExecutionParameters`). Here we
    just return the full CSV for the report and let `data_analytics` filter
    in-memory — but the contract `(sql, bind)` is the same one a real DB call
    would use.

    Args:
        report_name: Report whose mock dataset to return.
        sql: The SQL that would be sent to the database (logged for audit).
        bind: Bound parameters that would accompany `sql` (logged for audit).

    Returns:
        dict: {'success': bool, 'data': str (CSV), 'error': str or None}
    """
    logger.info(f"query_market_data report={report_name} sql={sql!r} bind={bind}")
    csv = MOCK_DATA.get(report_name)
    if csv is None:
        return {"success": False, "data": "", "error": f"Unknown report: {report_name}"}
    return {"success": True, "data": csv, "error": None}
