#!pip install pydoi
#!pip install pyDataverse==0.2.1
import requests
from urllib.request import urlopen
import mkwikidata
import subprocess
import json
import os
import io
#from pyDataverse.api import DataAccessApi
from pyDataverse.api import NativeApi
from pyDataverse.models import Dataset
from pyDataverse.api import Api
import re
import pydoi
from requests import delete
from requests import get
from requests import post
from requests import put
import urllib.request, json

class SemanticEnrichment():
    def __init__(self, config, complexquery=None, debug=False):
        self.config = config
        self.SKOSMOSHOST = False
        self.complexquery = ''
        if 'DEBUG' in os.environ:
            self.DEBUG = os.environ['DEBUG']
        else:
            self.DEBUG = False
        if complexquery:
            self.complexquery = complexquery
        else:
            if 'querytemplate' in os.environ:
                self.complexquery = os.environ['querytemplate']

    def set_skosmos(self, instanceurl):
        self.SKOSMOSHOST = instanceurl

    def set_base(self, base_url):
        self.base_url = base_url

    def set_solr(self, SOLR_URL):
        self.SOLR_url = SOLR_URL

    def republish_dataset(self, dataurl, PERSISTENT_IDENTIFIER, token=True):
        #try:
        if dataurl:
            headers = {'user-agent': 'my-app/0.0.1'}
            r = requests.get(dataurl, headers=headers)
            metadata = r.json()
            #with urllib.request.urlopen(dataurl) as url:
            #    metadata = json.load(url)
        #except:
            print("Resource not available or no access")

        url = "%s/api/dataverses/root/datasets/:import?pid=%s&release=yes" % (self.base_url, PERSISTENT_IDENTIFIER)
        for forbiddenfield in os.environ['forbiddenfields'].split(','):
            if forbiddenfield in metadata:
                del metadata[forbiddenfield]
        print(json.dumps(metadata))
        params = {'key': token }
        resp = post(
                url,
                data=json.dumps(metadata),
                params=params
        )
        return resp.text
    
    def query_geo_wikidata(self, q):
        query = """
SELECT DISTINCT ?cityLabel ?population ?gps
WHERE
{
  ?city wdt:P31/wdt:P279* wd:Q515 .
  ?city wdt:P1082 ?population .
  ?city wdt:P625 ?gps .
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY DESC(?population) LIMIT 100
"""
        query_result = mkwikidata.run_query(query, params={ })
        data = [{"name" : x["cityLabel"]["value"], "population" : int(x["population"]["value"])} for x in query_result["results"]["bindings"]]
        return data

    def external_CVs(self, queryparams, complexquery=False):
        print(queryparams)
        if self.complexquery:
            if 'fuzzy_search' in os.environ:
                if os.environ['fuzzy_search']:
                    complexquery = self.complexquery.replace('%%query%%', "%s*" % queryparams['query']).replace('%%fields%%', queryparams['fields']).replace('%%lang%%', queryparams['lang']).replace('%%vocab%%', queryparams['vocab'])
            else:
                complexquery = self.complexquery.replace('%%query%%', "%s" % queryparams['query']).replace('%%fields%%', queryparams['fields']).replace('%%lang%%', queryparams['lang']).replace('%%vocab%%', queryparams['vocab'])
        else:
            # query=%s*&fields=prefLabel&lang=nl&vocab=elsst-3
            if os.environ['fuzzy_search']:
                complexquery = "query=%s*&fields=%s&lang=%s&vocab=%s&querytype=V2" % (queryparams['query'], queryparams['fields'], queryparams['lang'], queryparams['vocab'])
            else:
                complexquery = "query=%s&fields=%s&lang=%s&vocab=%s&querytype=V2" % (queryparams['query'], queryparams['fields'], queryparams['lang'], queryparams['vocab'])
       
        url = "%s/rest/v1/search?query=%s" % (self.SKOSMOSHOST, complexquery)
        if self.DEBUG:
            print("[DEBUG URL] %s" % url)

        try:
            data = json.loads(requests.get(url).text)
            return data['results']
        except:
            return

    def dataverse_metadata(self, url):
        if not 'http' in url:
            url = url.replace('hdl:', '')
            url = url.replace('doi:', '')
            resolver = pydoi.resolve(url)['values']
            for item in resolver:
                if self.DEBUG:
                    print(item)
                if 'value' in item['data']:
                    check = re.search('http', str(item['data']['value']))
                    if check:
                        url = item['data']['value']
        
        urlchecker = re.search('^(\S+)\/\S+\?persistentId\=(\S+)', url)
        connector = {}
        data = []
        if urlchecker:
            connector['hostDOI'] = urlchecker.group(1)
            connector['thisDOI'] = urlchecker.group(2)
        if 'thisDOI' in connector:
            native_api = NativeApi(connector['hostDOI'])
            resp = native_api.get_dataset(connector['thisDOI'])
            # Get all datafiles related information
            data = resp.json()["data"]
        return data

    def skosmos_collect(self, url):
        skos_url = "%s/rest/v1/data?uri=%s" % (self.SKOSMOSHOST, url) + "&format=application/ld\%2Bjson"
        
        if self.DEBUG:
            print("[DEBUG SKOS] %s" % skos_url)
        content = json.loads(requests.get(skos_url).text)
        try:
            data = content['graph'][4]
        except:
            return []

        if self.DEBUG:
            print(json.dumps(data))

        keywords = []
        if 'altLabel' in data:
            for item in data['altLabel']:
                try:
                    q = "%s @%s" % (item['value'], item['lang'])
                    if not q in keywords:
                        keywords.append(q)
                except:
                    continue

        if 'prefLabel' in data:
            for item in data['prefLabel']:
                try:
                    if not os.environ['strict_lookup']:
                        q = "%s @%s" % (item['value'], item['lang'])
                        if not q in keywords:
                            keywords.append(q)
                    else:
                        # Strict match
                        if item['value'].lower() == q.lower():
                            if not q in keywords:
                                keywords.append(q)
                except:
                    continue
        return keywords

    def query_solr(self, query=False):
        if not query:
            query = "*.*"
        SOLR_API = "%s/solr/collection1/select?q=%s&wt=json&indent=true" % (self.SOLR_url, query)
        doc = json.loads(requests.get(SOLR_API).text)['response']['docs']
        del doc[0]['_version_']
        return doc[0]

    def collector(self, q):
        record = self.query_solr(q)
        vocitems = os.environ['CVfields'].split(',') # ['keywordValue', 'keywordValue_ss', 'topicClassValue']
        items = []
        keywords = []
        knownurl = {}
        for vocfield in vocitems:
            if vocfield in record:
                items.append(vocfield)

        for item in items:
            r = record[item]
            for q in r:
                if self.DEBUG:
                    print("Keyword: %s" % q)

                queryobject = { 'query': q, 'fields': '', 'vocab': '', 'lang': '' } 
                if 'skosmosendpoint' in self.config:
                    queryobject['skosmosendpoint'] = self.config['skosmosendpoint']
                    self.set_skosmos(self.config['skosmosendpoint'])
                else:
                    # Default Skosmos endpoint in .env
                    # example: https://thesauri.cessda.eu
                    if 'skosmosendpoint' in os.environ:
                        self.set_skosmos(os.environ['skosmosendpoint'])

                if 'fields' in self.config:
                    queryobject['fields'] = self.config['fields']
                if 'vocab' in self.config:
                    queryobject['vocab'] = self.config['vocab']
                if 'lang' in self.config:
                    queryobject['lang'] = self.config['lang']

                #for thisquery in queryobject['query'].split('/|  en |,'):
                for thisquery in re.split('/|  en |,', queryobject['query']):
                    thisqueryobject = queryobject
                    thisqueryobject['query'] = thisquery
                    data = self.external_CVs(queryobject)
                    if data:
                        for s in data:
                            print("[DEBUG RESULT1] %s" % s['prefLabels'])
                            for langproperty in s['prefLabels']:
                                langterm = "%s @%s" % (s['prefLabels'][langproperty], langproperty)
                                if not langterm in keywords:
                                    keywords.append(langterm)

        if keywords:
            record['keywordValue'] = keywords
            if self.DEBUG:
                for keyword in keywords:
                    print("\t[DEBUG ENRICHED KEYWORD] %s" % keyword)
        return record

