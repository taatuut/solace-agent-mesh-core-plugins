# Solace Agent Mesh Graph Database

A plugin that provides graph database query capabilities with natural language processing. Supports Neo4j databases.

NOTE: While the search action implies that it will not modify the database, it is very important that the credentials to the database for this action are read-only. This is because the natural language processing may not always generate the correct Cypher query and could potentially modify the database. Cypher is Neo4j's declarative and GQL conformant query language.

## Features

- Natural language to Cypher query conversion
- Support for multiple database types (Neo4j, TBD)
- Automatic schema detection with detailed metadata (A schema in Neo4j refers to indexes and constraints. Neo4j is often described as schema optional, meaning that it is not necessary to create indexes and constraints. You can create data — nodes, relationships and properties — without defining a schema up front.)
- Multiple response formats (YAML, JSON, CSV)
- Configurable query timeout
- Connection pooling and automatic reconnection
- CSV file import for database initialization (TODO: see https://neo4j.com/docs/getting-started/data-import/csv-import/ and https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/)

## Add a Graph Database Agent to SAM

Add the plugin to your SAM instance:

```sh
solace-agent-mesh plugin add sam_graph_database --pip -u git+https://github.com/taatuut/solace-agent-mesh-core-plugins#subdirectory=sam-graph-database
```

To instantiate the agent, you can use:

```sh
solace-agent-mesh add agent <new_agent_name> --copy-from sam_graph_database:graph_database
```

For example:

```sh
solace-agent-mesh add agent my_database --copy-from sam_graph_database:graph_database
```

This will create a new config file in the `configs/agents` directory with agent name you provided. You can view that configuration file to see the environment variables that need to be set (listed below).

## Environment Variables

The following environment variables are required for Solace connection:
- **SOLACE_BROKER_URL**
- **SOLACE_BROKER_USERNAME**
- **SOLACE_BROKER_PASSWORD**
- **SOLACE_BROKER_VPN**
- **SOLACE_AGENT_MESH_NAMESPACE**

For database connection:
- **<AGENT_NAME>_DB_TYPE** - One of: neo4j
- **<AGENT_NAME>_DB_HOST** - Database host (for Neo4j)
- **<AGENT_NAME>_DB_PORT** - Database port (for Neo4j)
- **<AGENT_NAME>_DB_USER** - Database user (for Neo4j)
- **<AGENT_NAME>_DB_PASSWORD** - Database password (for Neo4j)
- **<AGENT_NAME>_DB_NAME** - Database name or file path (for TBD)
- **<AGENT_NAME>_QUERY_TIMEOUT** - Query timeout in seconds (optional, default 30)
- **<AGENT_NAME>_DB_PURPOSE** - Description of the database purpose
- **<AGENT_NAME>_DB_DESCRIPTION** - Detailed description of the data
- **<AGENT_NAME>_AUTO_DETECT_SCHEMA** - Whether to automatically detect schema (optional, default true)
- **<AGENT_NAME>_DB_SCHEMA** - Database schema text (required if auto_detect_schema is false)
- **<AGENT_NAME>_SCHEMA_SUMMARY** - Natural language summary of the schema (required if auto_detect_schema is false)
- **<AGENT_NAME>_QUERY_EXAMPLES** - List of example natural language to GQL conformant query mappings like Cypher for Neo4j (optional)
- **<AGENT_NAME>_RESPONSE_GUIDELINES** - Guidelines to be attached to action responses (optional)

## Actions

### search_query
Execute natural language queries against the Graph database. The query is converted to GQL and results are returned in the specified format.

Parameters:
- **query** (required): Natural language description of the search query
- **response_format** (optional): Format of response (yaml, markdown, json, csv)
- **inline_result** (optional): Whether to return result inline or as file

If `response_guidelines` is configured, these guidelines will be included in the action response message.

## Multiple Database Support

You can add multiple Graph database agents to your SAM instance by:

1. Creating multiple copies of the config file
2. Giving each a unique name
3. Configuring different database connections
4. Using different agent names

This allows you to interact with multiple databases through natural language queries.

## Schema Detection

The agent can handle database schemas in two ways:

1. **Automatic Schema Detection** (default):
   - Automatically detects and analyzes the database schema
   - Generates a natural language summary of the schema
   - Includes table structures, column types, and relationships

2. **Manual Schema Configuration**:
   - Set `AUTO_DETECT_SCHEMA=false` to disable automatic detection
   - Provide `DB_SCHEMA` with the database structure description
   - Provide `SCHEMA_SUMMARY` with a natural language summary
   - Useful when you want to control exactly how the schema is presented to the agent

The schema information helps the LLM generate more accurate GQL queries from natural language.

## Query Examples

The Graph Database agent supports providing example queries to improve natural language to GQL conversion accuracy. This is particularly useful for:
- Teaching the agent about domain-specific terminology
- Demonstrating preferred query patterns
- Improving accuracy for complex queries
- Handling edge cases specific to your database

### How to Configure Query Examples

You can add query examples in your agent's YAML configuration file:

TODO: change query examples in below yaml fragment to GQL/Cypher, see https://neo4j.com/docs/python-manual/current/

```yaml
  # Other configuration...
  - component_name: action_request_processor
    # Other configuration...
    component_config:
      # Other configuration...
      query_examples:
        - natural_language: "Show me all employees in the Engineering department"
          gql_query: "SELECT * FROM employees WHERE department = 'Engineering'"
        - natural_language: "What are the top 5 highest paid employees?"
          gql_query: "SELECT name, salary FROM employees ORDER BY salary DESC LIMIT 5"
        - natural_language: "How many orders were placed last month?"
          gql_query: "SELECT COUNT(*) FROM orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
```
### Example Format and Usage

Each query example must include:
1. `natural_language`: The natural language question or request
2. `gql_query`: The corresponding GQL query that correctly answers the question

The agent will use these examples to better understand how to translate natural language queries into QQL for your specific database schema and domain.

## CSV File Import

The Graph Database agent supports importing CSV files to initialize or populate your database. This is particularly useful for:
- Setting up test databases
- Importing data from external sources
- Quickly populating databases with sample data

### How to Import CSV Files

You can directly edit your agent's YAML configuration file:

```yaml
  # Other configuration...
  - component_name: action_request_processor
    # Other configuration...
    component_config:
      # Other configuration...
      csv_files:
        - /path/to/file1.csv
        - /path/to/file2.csv
      csv_directories:
        - /path/to/csv/directory
```

### CSV File Format Requirements

For successful import:

1. The CSV file name (without extension) will be used as the table name
2. The first row must contain column headers that match your desired table column names
3. Data types will be inferred from the content
4. For best results, ensure data is clean and consistent

Example CSV file (`employees.csv`):
```
id,name,department,salary,company
1,John Doe,Engineering,75000,FunFactory
2,Jane Smith,Marketing,65000,FunFactory
3,Bob Johnson,Finance,80000,AutoCue
```

TODO:
Change:
This will create or populate a table named `employees` with the columns `id`, `name`, `department`, and `salary`.
Into something like:
This will create or populate a database named `employees` with edges `id`, `name`, `department`, `salary`, and `company` and relevant relations between them.

### Import Process

The CSV import happens automatically when the agent starts up. The process:

1. Reads each CSV file
2. Creates tables if they don't exist
3. Inserts data only for newly created tables
4. Handles data type conversion

If a table already exists, the agent will skip importing data for that table. This prevents accidental data modification of existing tables.
