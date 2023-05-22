# semantic-enrichment
Skosmos based semantic enrichment POC for Dataverse

## Docker deployment
Install Dataverse from Docker distribution and copy .env_sample by running command:
```
cp .env_sample .env
```
Build and run Semantic Enrichment as a service:
```
docker-compose build
docker-compose up -d
```
## Manual deployment
```
cp sample_config.py config.py
```
Fill config.py with your Dataverse token and base and run import script:
```
python3.8 import_pid.py
```
