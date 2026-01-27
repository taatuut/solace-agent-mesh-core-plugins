import re

VAR_PATTERN = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")

CYPHER_KEYWORDS = {
    "MATCH", "WITH", "RETURN", "WHERE", "ORDER", "BY",
    "COUNT", "DISTINCT", "AS", "AND", "OR", "CASE", "DESC", "LIMIT",
    "WHEN", "THEN", "ELSE", "END", "NULL", "TRUE", "FALSE",
    "TOFLOAT", "TOLONG", "TOSTRING"
}

def extract_variables(expr: str) -> set[str]:
    return {
        v for v in VAR_PATTERN.findall(expr)
        if v.upper() not in CYPHER_KEYWORDS
    }
