## Usage Example
```
from cypher.rewriter import CypherRewriter
from cypher.version import Neo4jVersion

rewriter = CypherRewriter(
    version=Neo4jVersion.V5,
    allow_apoc=False,
)

query = """
MATCH (t:Tournament)
WITH t, size((t)<-[:PART_OF]-()) AS match_count
RETURN t.name, match_count
ORDER BY match_count DESC
LIMIT 10
"""

safe_query = rewriter.rewrite(query)

print(safe_query)
print(rewriter.changes)
```

Output
```
MATCH (t:Tournament)
WITH t, COUNT { (t)<-[:PART_OF]-() } AS match_count
RETURN t.name, match_count
ORDER BY match_count DESC
LIMIT 10
```
```
[
  "Rewrote size((pattern)) → COUNT { }",
  "Query rewritten"
]
```

## Auto-Repair Coverage (What This Fixes)
Issue	                Auto-Repair
size((pattern))	        ✅ Rewritten
apoc.coll.toSet(x)	    ✅ Rewritten
APOC usage	            ❌ Rejected if unsafe
COUNT { RETURN ... }	❌ Rejected
Write queries	        ❌ Rejected
Neo4j 4 syntax	        ✅ Allowed

## How to Plug Into Your DB Service
```
rewriter = CypherRewriter(version=Neo4jVersion.V5)

def execute(query: str):
    safe = rewriter.rewrite(query)
    return session.run(safe)
```