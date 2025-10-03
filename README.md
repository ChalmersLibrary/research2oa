# research2oa

Script for matching Chalmers CRIS publication records with Open Alex contents.    

Will try to match (exact) using DOI and/or PMID first, then fuzzy match using title and (CRIS) publication year    
Output (tsv): CRIS Publication ID, CRIS Title, CRIS Year, CRIS DOI, CRIS PMID, Open Alex Publication ID, OA Title, OA Chalmers Affiliation (0/1), OA Reference Count, Match Type (DOI/PMID/Title/NO MATCH)    

Use .env file for configuration (see env_example)
