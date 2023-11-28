import mkwikidata
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from rdflib import Graph, URIRef, Literal, RDF, FOAF

class WikiPandas():
    def __init__(self, thisformat='json', debug=False):
        self.debug = debug
        self.format = thisformat
        self.state = 'default'
        
    def add_lang(self, data):
        langdata = []
        for item in data:
            if 'xml:lang' not in item['value']:
                item['value']['xml:lang'] = ''
            langdata.append(item)
        return langdata
    
    def set_state(self, newstate):
        self.state = newstate
        return self.state

    def wikidata_locations(self, wdt = "P279*", wd = "Q515"):
        query = """
        SELECT DISTINCT ?cityLabel ?population ?gps
        WHERE
        {
          ?city wdt:P31/wdt:%s wd:%s .
          ?city wdt:P1082 ?population .
          ?city wdt:P625 ?gps .
          SERVICE wikibase:label {
            bd:serviceParam wikibase:language "en" .
          }
        }
        ORDER BY DESC(?population) LIMIT 100
        """ % (wdt, wd)
        query_result = mkwikidata.run_query(query, params={ })
        if self.format == 'json':
            return query_result
        if self.format == 'pandas':
            data = [{"name" : x["cityLabel"]["value"], "population" : int(x["population"]["value"])} for x in query_result["results"]["bindings"]]
            df = pd.DataFrame(data).set_index("name")
            return df
        return

    def wikidata_entities(self, entityID="59269465"):
        query = """
        SELECT ?entity ?property ?propertyLabel ?value ?valueLabel
        WHERE {
          VALUES ?entity { wd:%s }
          ?entity ?property ?value.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        ORDER BY ?entity ?propertyLabel
        """ % entityID
        query_result = mkwikidata.run_query(query, params={ })
        self.format = 'pandas'
        if self.format == 'json':
            return query_result
        if self.format == 'pandas':
            langdata = self.add_lang(query_result["results"]["bindings"])
            data = [{"property" : x["property"]["value"], "value" : str(x["value"]["value"]), "lang": str(x["value"]["xml:lang"])} for x in langdata]
            df = pd.DataFrame(data).set_index("property")
            return df
        return
    
    def wikidata_persons(self, wdt="P214", personID="\"59269465\""):
        query = """
        PREFIX wikibase: <http://wikiba.se/ontology#>
        PREFIX wd: <http://www.wikidata.org/entity/> 
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?person ?personLabel ?property ?propertyLabel ?value WHERE {  
          ?person wdt:%s %s.
          ?person ?property ?value.
          SERVICE wikibase:label {
            bd:serviceParam wikibase:language "en" .
          }
        }
        """ % (wdt, personID)
        query_result = mkwikidata.run_query(query, params={ })
        if self.format == 'json':
            return query_result
        if self.format == 'pandas':
            langdata = self.add_lang(query_result["results"]["bindings"])
            data = [{"property" : x["property"]["value"], "value" : str(x["value"]["value"]), "lang": str(x["value"]["xml:lang"])} for x in langdata]
            df = pd.DataFrame(data).set_index("property")
            return df
        return

    def get_wikidata_ids_from_wikipedia_page(self, page_title, language='eu'):
        if isinstance(page_title, list):
            page_titles = page_title 
        else:
            page_titles = [ page_title ]
    
        pageids = {}
        for page in page_titles:
            pageitems = {}
            if 'http' in page:
                if '//wikipedia' in page:
                    langcheck = re.search(r'wikipedia.org\/wiki\/(\S+)', page)
                    if langcheck:
                        pageitems['page'] = langcheck.group(1)
                        pageitems['lang'] = 'eu'               
                else:
                    page = page.replace('www.','')
                    langcheck = re.search(r'\/\/(\S+?)\.wikipedia.org\/wiki\/(\S+)', page)
                    if langcheck:
                        pageitems['page'] = langcheck.group(2)
                        pageitems['lang'] = langcheck.group(1)
            if pageitems:
                # Construct the URL for the Wikidata API request
                api_url = "https://www.wikidata.org/w/api.php"
                params = {
                    "action": "wbgetentities",
                    "sites": f"{pageitems['lang']}wiki",
                    "titles": pageitems['page'],
                    "format": "json",
                }

                # Make the API request
                response = requests.get(api_url, params=params)
                data = response.json()
                entities = data.get("entities")
                if entities:
                    entity_id = next(iter(entities))
                    pageids[page] = entities[entity_id].get("id")
        return pageids
    
    def wikipedia_to_wikidata(self, wikipedia_url, exportformat='json'):
        exportformat = 'pandas'
        #wikipedia_url = "https://wikipedia.org/wiki/Heinrich_Finck"
        wikiuri = re.sub('^\S+wikipedia.org','',wikipedia_url)
        response = requests.get(wikipedia_url)
        soup = BeautifulSoup(response.text, "html.parser")
        entities = {}
        links = {}
        wiki = []
        images = {}
        graph = Graph()

        # Define a namespace for FOAF (Friend of a Friend) vocabulary
        FOAF_NS = FOAF
        filters = "Wikipedia:" #|Help:Contents"
        for a in soup.find_all("img"):
            if 'upload.wikimedia.org' in str(a):
                if not '.svg' in str(a):
                    if not 'http' in a['src']:
                        if not wikipedia_url in images:
                            images[wikipedia_url] = "http:%s" % a['src']
        print(images)
        for a in soup.find_all("a", href=True):
            entities = {}
            if a["href"]:
                link = a['href']
                if not 'http' in link:
                    link = "https://wikipedia.org%s" % link
        
                linktitle = a.get_text()
                if '/wiki/' in link:
                    checkwikifilter = False
                    thiswikiuri = re.sub('^\S+wikipedia.org','', link)
                    if wikiuri in thiswikiuri:
                        checkwikifilter = True
                    else:
                        checkwikifilter = re.search(r'Wikipedia:|Help:|Special:|Portal:|Talk:|Privacy_policy|Main_Page|Template|Template_talk|erms_of_Use', link)
                    if not checkwikifilter:
                        if not 'Category' in link:
                            linktype = 'concept'
                            entities[link] = linktitle 
                            graph.add((URIRef(link), RDF.type, FOAF.Person))
                            graph.add((URIRef(link), FOAF.name, Literal(a.get_text())))
                        else:
                            links[link] = linktitle
                            linktype = 'category'
                        entities = { 'wikilink': link, 'value': linktitle, 'type': linktype }
                        if not entities in wiki:
                            wiki.append(entities)
        if exportformat == 'json':
            return { 'entities': wiki, 'image': images }
        if exportformat == 'pandas':
            data = [{"property" : x["wikilink"], "value" : str(x["value"]), "type": str(x['type'])} for x in wiki]
            df = pd.DataFrame(data).set_index("property")
            return df
