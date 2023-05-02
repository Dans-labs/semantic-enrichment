from Semantics import SemanticEnrichment 
from config import SOLR, api_token, base_url, subdataverse
import json
import subprocess
import requests

config = {}
s = SemanticEnrichment(config, debug=True)
pid = "hdl:10622/FNKFSB"
dataurl = "https://datasets.iisg.amsterdam/api/datasets/export?exporter=dataverse_json&persistentId=%s" % pid
s.set_base(base_url) 
s.set_solr(SOLR)
resp = s.republish_dataset(dataurl, pid, api_token)
if 'data' in json.loads(resp):
    entityId = json.loads(resp)['data']['id']
else:
    entityId = s.dataverse_metadata("%s/dataset.xhtml?persistentId=%s" % (base_url, pid))['id']

if entityId:
    print(entityId)
    q = "entityId:%s" % entityId
    #s.set_skosmos("https://thesauri.cessda.eu")
    s.set_skosmos("https://finto.fi")
    record = s.collector(q)
    record_file = '/tmp/data.json'
    with open(record_file, 'w') as f:
        json.dump([record], f, indent=4)

    resp = requests.post("%s/solr/collection1/update?commit=true" % SOLR, headers={"Content-Type":"application/json"}, data=json.dumps([record]))
    print(resp.text)

