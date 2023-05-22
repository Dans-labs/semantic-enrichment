#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Developed by Slava Tykhonov and Eko Indarto
# Data Archiving and Networked Services (DANS-KNAW), Netherlands
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pyDataverse.api import Api, NativeApi
from pyDataverse.models import Datafile
from pyDataverse.models import Dataset
from pydantic import BaseModel
from typing import Optional
from starlette.responses import FileResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
#from src.model import Vocabularies, WriteXML
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from Semantics import SemanticEnrichment
import os
import json
import requests

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Dataverse Semantic Enrichment Service",
        description="Semantic driven API for Linked Open Data tasks.",
        version="0.1",
        routes=app.routes,
    )

    openapi_schema['tags'] = tags_metadata

    app.openapi_schema = openapi_schema
    return app.openapi_schema

tags_metadata = [
    {
        "name": "country",
        "externalDocs": {
            "description": "Put this citation in working papers and published papers that use this dataset.",
            "authors": 'Slava Tykhonov',
            "url": "https://dans.knaw.nl/en",
        },
    },
    {
        "name": "namespace",
        "externalDocs": {
            "description": "API endpoint for Dataverse semantic enrichment.",
            "authors": 'Slava Tykhonov',
            "url": "https://dans.knaw.nl",
        },
    }
]

app = FastAPI(
    openapi_tags=tags_metadata
)

app.mount('/static', StaticFiles(directory='static'), name='static')

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='https?://.*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.openapi = custom_openapi

@app.get('/version')
def version():
    return '0.1'

@app.get("/importdoi")
async def importdoi(token: str, pid: Optional[str] = None, base: Optional[str] = None):
    config = {}
    s = SemanticEnrichment(config, debug=True)
    #dataurl = "https://datasets.iisg.amsterdam/api/datasets/export?exporter=dataverse_json&persistentId=%s" % pid
    if base:
        dataurl = "https://%s/api/datasets/export?exporter=dataverse_json&persistentId=%s" % (base, pid)
    s.set_base(os.environ['base_url'])
    s.set_solr(os.environ['SOLR'])
    resp = s.republish_dataset(dataurl, pid, token)
    if 'data' in json.loads(resp):
        entityId = json.loads(resp)['data']['id']
    else:
        entityId = s.dataverse_metadata("%s/dataset.xhtml?persistentId=%s" % (os.environ['base_url'], pid))['id']

    if entityId:
        q = "entityId:%s" % entityId
        s.set_skosmos("https://thesauri.cessda.eu")
        #s.set_skosmos("https://finto.fi")
        record = s.collector(q)
        record_file = '/tmp/data.json'
        with open(record_file, 'w') as f:
            json.dump([record], f, indent=4)

        resp = requests.post("%s/solr/collection1/update?commit=true" % os.environ['SOLR'], headers={"Content-Type":"application/json"}, data=json.dumps([record]))
        return resp.text
    return

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9266)
