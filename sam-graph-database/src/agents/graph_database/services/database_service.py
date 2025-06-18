"""Service for handling GQL database operations."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import List, Dict, Any, Generator, Optional
# modules like sqlalchemy-neo4j, py2neo and metabase-neo4j-driver are not an option as these are EOL/abandoned
# so use official Neo4j module, might use neomodel
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError

from solace_ai_connector.common.log import log

from .csv_import_service import CsvImportService

class DatabaseService(ABC):
    """Abstract base class for database services."""

    def __init__(self, connection_params: Dict[str, Any], query_timeout: int = 30):
        """Initialize the database service.
        
        Args:
            connection_params: Database connection parameters
            query_timeout: Query timeout in seconds
        """
        self.connection_params = connection_params
        self.query_timeout = query_timeout
        self.driver = self._create_driver()
        self.csv_import_service = CsvImportService(self.driver)

    def import_csv_files(self, files: Optional[List[str]] = None,
                        directories: Optional[List[str]] = None) -> None:
        """Import CSV files into database tables.
        
        Args:
            files: List of CSV file paths
            directories: List of directory paths containing CSV files
        """
        self.csv_import_service.import_csv_files(files, directories)

    @abstractmethod
    def _create_driver(self) -> Driver:
        """Create Neo4j Driver for database connection.
        
        Returns:
            Neo4j Driver instance
        """
        pass

    @contextmanager
    def get_session(self) -> Generator[Driver.session, None, None]: # NOTE: Use Session or Driver.session? Test!
        """Get a database session from the pool.
        
        Yields:
            Active database session
            
        Raises:
            Neo4jError: If session fails
        """
        try:
            session = self._driver.session()
            yield session
        except Neo4jError as e:
            log.error("Database connection error: %s", str(e), exc_info=True)
            raise
        finally:
            session.close()

    def close(self):
        self._driver.close()

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a GQL query.
        
        Args:
            query: GQL query to execute
            
        Returns:
            List of dictionaries containing query results
            
        Raises:
            Neo4jError: If query execution fails
        """
        try:
            with self.get_session() as session:
                result = session.run(query)
                return list(result.mappings())
        except Neo4jError as e:
            log.error("Query execution error: %s", str(e), exc_info=True)
            raise

    def get_indexes(self, database: str) -> List[Dict[str, Any]]:
        """Get indexes for a database.
        
        Args:
            table: Database name
            
        Returns:
            List of index details
        """
        
        with self.driver.session() as session:
            return self._run_query(session, "CALL db.indexes()", "index")

    # NOTE: fucntion needs to be rewritten, currently not in use
    def get_unique_values(self, table: str, column: str, limit: int = 3) -> List[Any]:
        """Get sample of unique values from a column.
        
        Args:
            table: Table name
            column: Column name
            limit: Maximum number of values to return
            
        Returns:
            List of unique values
        """
        if self.driver.name == 'neo4j':
            # Neo4j uses rand()
            query = f"MATCH (n) WITH DISTINCT n ORDER BY rand() RETURN n LIMIT {limit}"
        else:
            # TBD uses RANDOM()
            query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY RANDOM() LIMIT {limit}"
        results = self.execute_query(query)
        return [row[column] for row in results]

    # NOTE: fucntion needs to be rewritten, currently not in use
    def get_column_stats(self, table: str, column: str) -> Dict[str, Any]:
        """Get basic statistics for a column.
        
        Args:
            table: Table name
            column: Column name
            
        Returns:
            Dictionary of statistics (min, max, avg, etc.)
        """
        query = f"""
            SELECT 
                COUNT(*) as count,
                COUNT(DISTINCT {column}) as unique_count,
                MIN({column}) as min_value,
                MAX({column}) as max_value
            FROM {table}
            WHERE {column} IS NOT NULL
        """
        results = self.execute_query(query)
        return results[0] if results else {}

class Neo4jService(DatabaseService):
    """Neo4j database service implementation."""

    def _create_driver(self) -> Driver:
        """Create Neo4j database driver."""
        port=self.connection_params.get("port")
        database=self.connection_params.get("database")
        return GraphDatabase.driver(self.connection_params.get("host"), auth=(self.connection_params.get("user"), self.connection_params.get("password")))


class TBDService(DatabaseService):
    """TBD database service implementation."""
    
    def _create_driver(self) -> Driver:
        """Create TBD database driver."""
        port=self.connection_params.get("port")
        database=self.connection_params.get("database")
        return GraphDatabase.driver(self.connection_params.get("host"), auth=(self.connection_params.get("user"), self.connection_params.get("password")))
