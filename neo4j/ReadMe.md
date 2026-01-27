# Neo4J database

This folder contains a docker compose file to start a Neo4J database.

## Prepare Neo4J
Prepare a .env file with the following parameters (see sample.env):
```
NEO4J_USERNAME = [username]
NEO4J_PASSWORD = [password]
NEO4J_URI = neo4j://localhost:7687
```

## Start Neo4J
```
docker compose -d start
```

## Stop Neo4J
```
docker compose stop
```

## Remove Neo4J
```
docker compose down -v
```


The Python script ingest_football_data.py will load a set of soccer match related data into the database. The data comes from https://github.com/martj42/international_results. Check the readme for that repo for info on the data used.

```
python3 ingest_football_data.py
```
