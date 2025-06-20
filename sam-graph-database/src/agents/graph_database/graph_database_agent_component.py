"""The agent component for the graph database"""

import os
import copy
import sys
from typing import Dict, Any, Optional, List
import yaml
import json
import pprint
from neo4j.graph import Node, Relationship

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from solace_ai_connector.common.log import log
from solace_agent_mesh.agents.base_agent_component import (
    agent_info,
    BaseAgentComponent,
)

from .services.database_service import (
    DatabaseService,
    Neo4jService,
    TBDService
)
from .actions.search_query import SearchQuery

info = copy.deepcopy(agent_info)
info.update(
    {
        "agent_name": "graph_database",
        "class_name": "GraphDatabaseAgentComponent",
        "description": "Graph Database agent for executing natural language queries against graph databases",
        "config_parameters": [
            {
                "name": "agent_name",
                "required": True,
                "description": "Name of this graph database agent instance",
                "type": "string"
            },
            {
                "name": "db_type",
                "required": True,
                "description": "Database type (Neo4j, TBD)",
                "type": "string"
            },
            {
                "name": "host",
                "required": False,
                "description": "Database host (for Neo4j)",
                "type": "string"
            },
            {
                "name": "port",
                "required": False,
                "description": "Database port (for Neo4j)",
                "type": "integer"
            },
            {
                "name": "user",
                "required": False,
                "description": "Database user (for Neo4j)",
                "type": "string"
            },
            {
                "name": "password",
                "required": False,
                "description": "Database password (for Neo4j)",
                "type": "string"
            },
            {
                "name": "database",
                "required": True,
                "description": "Database name (or file path for TBD)",
                "type": "string"
            },
            {
                "name": "query_timeout",
                "required": False,
                "description": "Query timeout in seconds",
                "type": "integer",
                "default": 30
            },
            {
                "name": "database_purpose",
                "required": True,
                "description": "Purpose of the database",
                "type": "string"
            },
            {
                "name": "data_description",
                "required": False,
                "description": "Detailed description of the data held in the database. Will be auto-detected if not provided.",
                "type": "string"
            },
            {
                "name": "auto_detect_schema",
                "required": False,
                "description": "Automatically create a schema based on the database structure",
                "type": "boolean",
                "default": True
            },
            {
                "name": "database_schema",
                "required": False,
                "description": "Database schema if auto_detect_schema is False",
                "type": "string"
            },
            {
                "name": "schema_summary",
                "required": False,
                "description": "Summary of the database schema if auto_detect_schema is False. Will be used in agent description.",
                "type": "string"
            },
            {
                "name": "query_examples",
                "required": False,
                "description": "Natural language to Cypher query examples to help the agent understand how to query the database. Format: List of objects with 'natural_language' and 'cypher_query' keys. Will be attached to the schema when auto_detect_schema is False.",
                "type": "list"
            },
            {
                "name": "csv_files",
                "required": False,
                "description": "List of CSV files to import as tables on startup",
                "type": "list"
            },
            {
                "name": "csv_directories",
                "required": False,
                "description": "List of directories to scan for CSV files to import as tables on startup",
                "type": "list"
            },
            {
                "name": "response_guidelines",
                "required": False,
                "description": "Guidelines to be attached to action responses. These will be included in the response message.",
                "type": "string"
            }
        ]
    }
)

class GraphDatabaseAgentComponent(BaseAgentComponent):
    """Component for handling graph database operations."""

    info = info
    actions = [SearchQuery]

    def __init__(self, module_info: Dict[str, Any] = None, **kwargs):
        """Initialize the Graph Database agent component.

        Args:
            module_info: Optional module configuration.
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If required database configuration is missing.
        """
        module_info = module_info or info
        super().__init__(module_info, **kwargs)

        self.agent_name = self.get_config("agent_name")
        self.db_type = self.get_config("db_type")
        self.database_purpose = self.get_config("database_purpose")
        self.data_description = self.get_config("data_description")
        self.auto_detect_schema = self.get_config("auto_detect_schema", True)
        self.query_timeout = self.get_config("query_timeout", 30)
        self.response_guidelines = self.get_config("response_guidelines", "")

        self.action_list.fix_scopes("<agent_name>", self.agent_name)
        module_info["agent_name"] = self.agent_name

        # Initialize database handler
        self.db_handler = self._create_db_handler()

        # Import any configured CSV files
        csv_files = self.get_config("csv_files", [])
        csv_directories = self.get_config("csv_directories", [])
        if csv_files or csv_directories:
            try:
                self.db_handler.import_csv_files(csv_files, csv_directories)
            except Exception as e:
                #log.error("Error importing CSV files: %s", str(e))
                log.error(f"Error importing CSV files: {str(e)}")

        # Get schema information
        if self.auto_detect_schema:
            schema_dict = self._detect_schema()
            print("bo ez schema_dict")
            print()
            #print(json.dumps(schema_dict, indent=2))
            pprint.pprint(schema_dict)
            print()
            print("eo ez schema_dict")
            # Clean the schema before converting to YAML
            schema_dict_cleaned = self._clean_schema(schema_dict)
            print("bo ez schema_dict_cleaned")
            print()
            #print(json.dumps(schema_dict_cleaned, indent=2))
            pprint.pprint(schema_dict_cleaned)
            print()
            print("eo ez schema_dict_cleaned")
            # Convert dictionary to YAML string
            schema_yaml = yaml.dump(schema_dict_cleaned, default_flow_style=False, allow_unicode=True)
            self.detailed_schema = schema_yaml
            print("bo ez schema_yaml")
            print()
            pprint.pprint(schema_yaml)
            print()
            print("eo ez schema_yaml")
            # Generate schema prompt from detected schema
            self.schema_summary = self._get_schema_summary()
            if not self.schema_summary:
                raise ValueError("Failed to generate schema summary from auto-detected schema")
        else:
            # Get schema from config
            schema = self.get_config("database_schema")
            if schema is None:
                raise ValueError(
                    "database_schema is required when auto_detect_schema is False. "
                    "This text should describe the database structure."
                )
            elif isinstance(schema, dict):
                # Convert dictionary to YAML string
                self.detailed_schema = yaml.dump(schema, default_flow_style=False)
            else:
                # Already a string, use as is
                self.detailed_schema = str(schema)
            # Get query examples if provided
            query_examples = self.get_config("query_examples")
            if query_examples:
                # Format query examples with clear separation and structure
                formatted_examples = "EXAMPLE QUERIES:\n"
                formatted_examples += "=================\n\n"
                
                # Process examples from the list of dictionaries
                for i, example in enumerate(query_examples, 1):
                    if isinstance(example, dict) and "natural_language" in example and "cypher_query" in example:
                        formatted_examples += f"Example {i}:\n"
                        formatted_examples += f"Natural Language: {example['natural_language'].strip()}\n"
                        formatted_examples += f"Cypher Query: {example['cypher_query'].strip()}\n\n"
                
                # Attach formatted examples to the schema
                self.detailed_schema = f"{self.detailed_schema}\n\n{formatted_examples}"
            
            # Only use provided schema_summary, don't try to generate one
            self.schema_summary = self.get_config("schema_summary")
            if not self.schema_summary:
                raise ValueError(
                    "schema_summary is required when auto_detect_schema is False. "
                    "This text should describe the database schema in natural language "
                    "to help the agent understand how to query the database."
                )
        
        # Update the search_query action with schema information
        for action in self.action_list.actions:
            if action.name == "search_query":
                current_directive = action._prompt_directive
                schema_info = f"\n\nDatabase Schema:\n{self.schema_summary}"
                action._prompt_directive = current_directive + schema_info
                break

        # Generate and store the agent description
        self._generate_agent_description()

    def _create_db_handler(self) -> DatabaseService:
        """Create appropriate database handler based on configuration.
        
        Returns:
            Database service instance
            
        Raises:
            ValueError: If database configuration is invalid
        """
        connection_params = {
            "database": self.get_config("database"),
        }

        if self.db_type in ("neo4j", "TBD"):
            # Add connection parameters needed for Neo4j, TBD
            connection_params.update({
                "host": self.get_config("host"),
                "port": self.get_config("port"),
                "user": self.get_config("user"),
                "password": self.get_config("password"),
            })

        if self.db_type == "neo4j":
            return Neo4jService(connection_params, query_timeout=self.query_timeout)
        elif self.db_type in ("TBD", "anotherTBDGraphDB"):
            return TBDService(connection_params, query_timeout=self.query_timeout)
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def _detect_schema(self) -> Dict[str, Any]:
        """Detect database schema including distinct node types (labels), distinct relationship types, keys used in nodes/relationship.

        Returns:
            Dictionary containing detailed schema information
        """

        def serialize_neo4j_schema(raw_schema):
            def convert(item):
                if isinstance(item, Node):
                    return {
                        "id": item.id,
                        "labels": list(item.labels),
                        "properties": dict(item)
                    }
                elif isinstance(item, Relationship):
                    return {
                        "id": item.id,
                        "type": item.type,
                        "start_node": item.start_node.id,
                        "end_node": item.end_node.id,
                        "properties": dict(item)
                    }
                elif isinstance(item, list):
                    return [convert(i) for i in item]
                elif isinstance(item, dict):
                    return {k: convert(v) for k, v in item.items()}
                else:
                    return item

            return convert(raw_schema)

        def get_schema(tx, *args, **kwargs):
            result = tx.run("CALL db.schema.visualization()")
            serialized_schema = serialize_neo4j_schema(result)
            serialized_schema = dict(serialized_schema.single())
            print("bo ez serialized_schema")
            print()
            pprint.pprint(serialized_schema)
            print()
            print("eo ez serialized_schema")
            #return dict(result.single())
            return serialized_schema

        with self.db_handler.driver.session() as session:
            schema = session.execute_read(get_schema)

        return schema

    def _run_query(self, session, query: str, key: str) -> list:
        result = session.run(query)
        return [record[key] for record in result]
    
    def _clean_schema(self, schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Clean the schema dictionary by removing problematic fields.
        
        Args:
            schema_dict: The schema dictionary to clean
            
        Returns:
            Cleaned schema dictionary
        """

        # NOTE: no code for checking/cleaning implemented yet, just pass back schema assumign it is ok 
        return schema_dict

    def _get_schema_summary(self) -> str:
        """Gets a terse formatted summary of the database schema.

        Returns:
            A string with a one-line summary of each table and its columns.
        """
        if not self.detailed_schema:
            return "Schema information not available."

        try:
            schema_dict = yaml.safe_load(self.detailed_schema)  # Convert YAML to dictionary
            if not isinstance(schema_dict, dict):
                raise ValueError("Error: Parsed schema is not a valid dictionary.")

        except yaml.YAMLError as exc:
            raise ValueError(f"Error: Failed to parse schema. Invalid YAML format. Details: {exc}") from exc

        # Construct summary lines
        summary_lines = json.dumps(schema_dict, separators=(",", ":"))

        return "\n".join(summary_lines)

    def _generate_agent_description(self):
        """Generate and store the agent description."""
        description = f"This agent provides read-only access to a {self.db_type} database.\n\n"

        if self.database_purpose:
            description += f"Purpose:\n{self.database_purpose}\n\n"

        if self.data_description:
            description += f"Data Description:\n{self.data_description}\n"
        
        # Extract table information if schema exists
        try:
            schema_dict = yaml.safe_load(self.detailed_schema)
            if isinstance(schema_dict, dict) and schema_dict:
                tables = list(schema_dict.keys())
                description += f"Contains {len(tables)} tables: {', '.join(tables)}\n"
        except yaml.YAMLError:
            pass  # Silently fail if YAML parsing fails

        self._agent_description = {
            "agent_name": self.agent_name,
            "description": description.strip(),
            "always_open": self.info.get("always_open", False),
            "actions": self.get_actions_summary(),
        }

    def get_agent_summary(self):
        """Get a summary of the agent's capabilities."""
        return self._agent_description
    
    def get_db_handler(self) -> DatabaseService:
        """Get the database handler instance."""
        return self.db_handler
