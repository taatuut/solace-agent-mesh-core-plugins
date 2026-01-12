from .versions import Neo4jVersion
from .rules import (
    SIZE_PATTERN,
    APOC_PATTERN,
    COUNT_RETURN_PATTERN,
    COLLECT_RETURN_PATTERN,
    TOSTRING_PATTERN,
    rewrite_size_to_count,
    rewrite_apoc_to_native,
)
from .exceptions import UnsafeCypherError


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

    # ------------------
    # Neo4j 5 rules
    # ------------------

    def _rewrite_for_v5(self, query: str) -> str:
        q = query

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
