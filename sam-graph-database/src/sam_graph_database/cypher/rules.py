import re

# --------
# Patterns
# --------

SIZE_PATTERN = re.compile(r"size\s*\(\s*\((.*?)\)\s*\)", re.IGNORECASE)
WITH_PATTERN = re.compile(r"with\s*\.", re.IGNORECASE)
APOC_PATTERN = re.compile(r"\bapoc\.", re.IGNORECASE)
COUNT_RETURN_PATTERN = re.compile(r"count\s*\{\s*return", re.IGNORECASE)
COLLECT_RETURN_PATTERN = re.compile(r"collect\s*\{\s*return", re.IGNORECASE)
TOSTRING_PATTERN = re.compile(
    r"toString\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)",
    re.IGNORECASE,
)

# --------
# Rewriters
# --------

def rewrite_size_to_count(match: re.Match) -> str:
    """
    size((a)--())  -> COUNT { (a)--() }
    """
    pattern = match.group(1)
    return f"COUNT {{ ({pattern}) }}"


def rewrite_apoc_to_native(query: str) -> str:
    """
    Replace apoc.coll.toSet(x) -> collect(DISTINCT x)
    """
    query = re.sub(
        r"apoc\.coll\.toSet\s*\(\s*([^)]+)\s*\)",
        r"collect(DISTINCT \1)",
        query,
        flags=re.IGNORECASE,
    )
    return query
