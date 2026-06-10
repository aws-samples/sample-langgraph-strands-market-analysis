
def sql_column_validation(columns):
    """Validate and clean column names for SQL safety."""
    # Build column list for SELECT statement
    if isinstance(columns, list) and len(columns) > 0:
        allowed_sql_chars = set('_.*()+-/%, ')
        clean_columns = []
        for col in columns:
            if isinstance(col, str) and col.strip():
                # Basic sanitization - only allow alphanumeric, underscore, and common SQL characters
                safe_chars = all(c.isalnum() or c in allowed_sql_chars for c in col)
                if not safe_chars:
                    filtered_col = ''.join(c for c in col if c.isalnum() or c in allowed_sql_chars)
                    clean_columns.append(filtered_col)
                else:
                    clean_columns.append(col)  # Keep the original expression
        
        if not clean_columns:
            raise ValueError("No valid columns provided")
        
        columns_str = ', '.join(clean_columns)
    else:
        raise ValueError("Columns list cannot be empty")
    
    return columns_str


def table_name_validation(table):
    """Validate and clean table name for SQL safety."""
    # Basic sanitization - only allow alphanumeric, underscore, and common SQL characters
    clean_table = ''.join(c for c in table if c.isalnum() or c in ['_', '.'])
    if not clean_table:
        raise ValueError("Invalid table name")
    return clean_table


def sql_order_by_validation(order_by_list):
    """Validate and clean ORDER BY clause for SQL safety."""
    if not order_by_list:
        return ""
    
    allowed_chars = set('_. ()')  # Added parentheses for SQL functions
    allowed_keywords = {'ASC', 'DESC', 'asc', 'desc'}  # Allow both cases
    clean_columns = []
    
    for item in order_by_list:
        if not isinstance(item, str):
            continue
        
        item = item.strip()
        if not item:
            continue
        
        # Split by spaces to handle 'column ASC/DESC' format
        parts = item.split()
        if len(parts) > 2:
            # Too many parts, skip this item
            continue
        
        # Validate column name (first part)
        column = parts[0]
        safe_column = all(c.isalnum() or c in allowed_chars for c in column)
        if not safe_column:
            continue
        
        clean_item = column
        
        # Validate direction (second part if exists) - preserve original case
        if len(parts) == 2:
            direction = parts[1]
            if direction.upper() in {'ASC', 'DESC'}:  # Check uppercase but preserve original
                clean_item += f" {direction}"
            # If direction is invalid, just use column name
        
        clean_columns.append(clean_item)
    
    return ", ".join(clean_columns) if clean_columns else ""


def sql_group_by_validation(group_by_list):
    """Validate and clean GROUP BY clause for SQL safety."""
    if not group_by_list:
        return ""
    
    allowed_chars = set('_. ')
    clean_columns = []
    
    for item in group_by_list:
        if not isinstance(item, str):
            continue
        
        item = item.strip()
        if not item:
            continue
        
        # Only allow alphanumeric characters, underscores, dots, and spaces
        safe_column = all(c.isalnum() or c in allowed_chars for c in item)
        if safe_column:
            clean_columns.append(item)
    
    return ", ".join(clean_columns) if clean_columns else ""
