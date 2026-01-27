# solace-agent-mesh-core-plugins

## Prerequisites
- Python 3.10.16+
- pip (usually included with Python) or uv (install uv)
- Operating System: macOS, Linux, or Windows (via WSL)
- LLM API key from any major provider or your own custom endpoint
- virtual environment
- solace-agent-mesh
- docker

``` MacOs
python3 -m venv .venv
source .venv/bin/activate
pip install solace-agent-mesh
```

``` Windows
python3 -m venv .venv
source .venv/bin/activate
pip install solace-agent-mesh
```

See (create agents)[https://solacelabs.github.io/solace-agent-mesh/docs/documentation/developing/create-agents] documentation for an explanation on how to build custom agents

## Build the plugin
```
pip install build # (one-time installation of python build tools)
pushd sam-graph-database
sam plugin build
popd
```

This will create the wheel file in the dist folder.

## Start Neo4J

This part will start a Neo4J database in a docker container. See the readme file in the folder neo4j to spin ity up and give it an initial load

## Start Solace Agent Mesh

After starting the Neo4J container you can run the Solace Agent Mesh with the new graph agent.
To use this plugin in your Agent Mesh project:
```
cd into your Agent Mesh project (not this folder)
# optionally uninstall a previous version
pip uninstall -y sam-graph-agent
sam plugin add sam-graph-agent --plugin PATH/TO/sam-graph-database/dist/sam_graph_database-*.whl
```

This will install the sam-graph-agent into your agent mesh and you should be able to see the agent card in the Solace Agent Mesh UI

```
solace-agent-mesh run
```

Now you can start the SAM by hitting http://localhost:8000 in your favorite browser


If you want to make changes in the sam-graph-agent, you go back to the sam-graph-agent folder redo your work and rebuild
