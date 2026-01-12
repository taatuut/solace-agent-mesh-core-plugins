class CypherRewriteError(Exception):
    pass


class UnsafeCypherError(CypherRewriteError):
    pass
