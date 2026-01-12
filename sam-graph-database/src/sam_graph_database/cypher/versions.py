from enum import Enum

class Neo4jVersion(Enum):
    V4 = "4"
    V5 = "5"


def detect_version(version_string: str) -> Neo4jVersion:
    """
    Detect Neo4j version from version string.

    Supports both semantic versioning and calendar-based versioning:
      - Semantic: '5.12.0', '4.4.18'
      - Calendar: '2025.11.2' (treated as V5+)

    Args:
        version_string: Version string from Neo4j

    Returns:
        Neo4jVersion enum value (V4 or V5)
    """
    major = version_string.split(".")[0]
    major_int = int(major)

    # Calendar-based versioning (2025+) is Neo4j 5+
    # Semantic versioning: 5+ is V5, 4 and below is V4
    if major_int >= 5:
        return Neo4jVersion.V5
    return Neo4jVersion.V4

