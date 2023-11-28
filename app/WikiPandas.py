import mkwikidata
import pandas as pd

class WikiPandas():
    def __init__(self, thisformat='json', debug=False):
        self.debug = debug
        self.format = thisformat
        
    def add_lang(self, data):
        langdata = []
        for item in data:
            if 'xml:lang' not in item['value']:
                item['value']['xml:lang'] = ''
            langdata.append(item)
        return langdata
    
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
