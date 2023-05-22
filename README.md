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
Import any dataset with pid from Dataverse network by running this command with appropriate base and token for your local Dataverse, for example:
```
curl "http://0.0.0.0:8099/importdoi?token=token-f853-cd0e-486c-a950-90050eb6aa63&pid=doi:10.57934/0b01e410806b1d9d&base=portal.odissei.nl"
```
It will create in your local Dataverse enriched dataset index with properties from ELLST controlled vocabulary. For example, you can search in any available language and should be able to find metadata records in Dutch or French.
## Manual deployment
```
cp sample_config.py config.py
```
Fill config.py with your Dataverse token and base and run import script:
```
python3.8 import_pid.py
```
