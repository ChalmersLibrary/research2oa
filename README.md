# research2oa

Script for matching Chalmers CRIS publication records with Open Alex contents.    

Will try to match (exact) using DOI and/or PMID first, then fuzzy match using title and (CRIS) publication year.   

If Scopus EID is present in the CRIS record it will also do a simultaneous Scopus API cross lookup to retrieve the Scopus citation count (if available) for comparison.      

Output (tsv): 
* CRIS Publication ID
* CRIS Title
* CRIS Publ Year 
* DOI
* PMID
* Open Alex Publication (Work) ID
* OA Chalmers Affiliation (0/1)
* OA Citation Count
* Scopus Citation Count
* Match Type (DOI/PMID/TITLE/NO MATCH)      

Use .env file for configuration (see env_example)
