from .versions import Neo4jVersion
from .rules import (
    SIZE_PATTERN,
    WITH_PATTERN,
    APOC_PATTERN,
    COUNT_RETURN_PATTERN,
    COLLECT_RETURN_PATTERN,
    TOSTRING_PATTERN,
    rewrite_size_to_count,
    rewrite_apoc_to_native,
)
from .exceptions import UnsafeCypherError
from .utils import extract_variables
import re

class CypherRewriter:
    """
    Version-aware Cypher rewriter with auto-repair.
    """

    def __init__(
        self,
        version: Neo4jVersion,
        allow_apoc: bool = False,
        strict: bool = True,
    ):
        self.version = version
        self.allow_apoc = allow_apoc
        self.strict = strict
        self.changes: list[str] = []

    # ------------------
    # Public API
    # ------------------

    def rewrite(self, query: str) -> str:
        original = query
        q = query.strip()

        if self.version == Neo4jVersion.V5:
            q = self._rewrite_for_v5(q)

        self._final_validation(q)

        if q != original:
            self.changes.append("Query rewritten")

        return q

    def _sanitize_with_clause(self, query: str) -> str:
        """
        Remove any undefined or phantom variables from WITH clauses.
        This prevents errors like 'Variable `density_score` not defined'.
        """
        parts = query.split("WITH")
        if len(parts) < 2:
            return query

        sanitized = parts[0]  # everything before first WITH
        defined_vars = set()

        for part in parts[1:]:
            # Split line + rest of query
            if "\n" in part:
                line, rest = part.split("\n", 1)
            else:
                line, rest = part, ""

            # Extract all comma-separated items
            items = [i.strip() for i in line.split(",")]

            valid_items = []
            for item in items:
                # Get variable being declared or used
                # Handle aliases: COUNT(r) AS total_edges -> total_edges
                if " AS " in item.upper():
                    var = item.upper().split(" AS ")[-1].strip()
                else:
                    var = item.split()[-1]

                # Keep if already defined or new expression
                # Expression detected if contains "(" or "="
                if var in defined_vars or "(" in item or "=" in item:
                    valid_items.append(item)
                    defined_vars.add(var)
                else:
                    # skip phantom variable
                    self.changes.append(f"Removed undefined variable from WITH: {var}")

            sanitized += "WITH " + ", ".join(valid_items) + "\n" + rest

            # Update defined_vars from this line
            for item in valid_items:
                # capture declared alias after AS
                m = re.search(r"AS\s+([a-zA-Z_][a-zA-Z0-9_]*)", item, re.IGNORECASE)
                if m:
                    defined_vars.add(m.group(1))
                # capture variable names used directly
                for v in extract_variables(item):
                    defined_vars.add(v)

        return sanitized

    def _rewrite_to_string_on_nodes(self, query: str) -> str:
        """
        Rewrite toString(nodeVar) into a safe representation.
        """

        def replacer(match: re.Match) -> str:
            var = match.group(1)

            # Heuristic 1: if `.name` is referenced anywhere, prefer it
            if f"{var}.name" in query:
                self.changes.append(
                    f"Rewrote toString({var}) → toString({var}.name)"
                )
                return f"toString({var}.name)"

            # Heuristic 2: structured map fallback (LLM-safe)
            self.changes.append(
                f"Rewrote toString({var}) → node map representation"
            )
            return (
                "{ labels: labels("
                + var
                + "), properties: properties("
                + var
                + ") }"
            )

        return TOSTRING_PATTERN.sub(replacer, query)

    def _repair_with_scope(self, query: str) -> str:
        """
        Ensure variables used after WITH are preserved.
        """

        parts = query.split("WITH")
        if len(parts) < 2:
            return query  # no WITH → nothing to repair

        before_with = parts[0]
        after_with = "WITH".join(parts[1:])

        # Extract variables used in RETURN
        return_match = re.search(r"RETURN\s+(.*)", after_with, re.IGNORECASE | re.DOTALL)
        if not return_match:
            return query

        return_vars = extract_variables(return_match.group(1))

        # Extract variables declared in WITH
        with_line = after_with.split("\n", 1)[0]
        declared_vars = extract_variables(with_line)

        missing = return_vars - declared_vars
        if not missing:
            return query

        # Repair WITH
        repaired_with = with_line.rstrip() + ", " + ", ".join(sorted(missing))
        repaired_query = query.replace(with_line, repaired_with, 1)

        self.changes.append(
            f"Repaired WITH clause to preserve variables: {', '.join(sorted(missing))}"
        )

        return repaired_query

    # ------------------
    # Neo4j 5 rules
    # ------------------

    def _rewrite_for_v5(self, query: str) -> str:
        q = query

        # Step 0: sanitize phantom WITH variables
        if WITH_PATTERN.search(q):
            q = self._sanitize_with_clause(q)
            self.changes.append("Rewrote WITH patterns to remove undefined variables")

        # 1️⃣ Rewrite size((pattern)) → COUNT { (pattern) }
        if SIZE_PATTERN.search(q):
            q = SIZE_PATTERN.sub(rewrite_size_to_count, q)
            self.changes.append("Rewrote size((pattern)) → COUNT { }")

        # 2️⃣ APOC handling
        if APOC_PATTERN.search(q):
            if not self.allow_apoc:
                q = rewrite_apoc_to_native(q)
                if APOC_PATTERN.search(q):
                    raise UnsafeCypherError("APOC usage is not allowed in Neo4j 5")
                self.changes.append("Rewrote APOC to native Cypher")

        # 3️⃣ Invalid COUNT { RETURN ... }
        if COUNT_RETURN_PATTERN.search(q):
            raise UnsafeCypherError("COUNT { RETURN ... } is invalid Cypher")

        if COLLECT_RETURN_PATTERN.search(q):
            raise UnsafeCypherError("collect { RETURN ... } is invalid Cypher")

        if TOSTRING_PATTERN.search(q):
            q = self._rewrite_to_string_on_nodes(q)

        q = self._repair_with_scope(q)

        return q

    # ------------------
    # Final validation
    # ------------------

    def _final_validation(self, query: str):
        q = query.lower()

        forbidden = [
            "call dbms",
            "drop ",
            "delete ",
            "set ",
            "create ",
            "merge ",
        ]

        for f in forbidden:
            if f in q:
                raise UnsafeCypherError(f"Forbidden operation detected: {f}")
