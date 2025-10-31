#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import os

# Script for matching Chalmers CRIS publication records with Open Alex, Scopus and OpenAIRE (BIP) contents
# See README for usage instructions and details
  
# Variables
checked = 0
oa_match = 0
oa_match_doi = 0
oa_match_title = 0
oa_match_pmid = 0
oa_match_other = 0
no_oa_match = 0
offset = 0
rows_per_query = 100

load_dotenv()
oa_url = os.getenv("OA_API_ENDPOINT")
start_year = os.getenv("START_YEAR")
cris_api_user = os.getenv("CRIS_API_USER")
cris_api_pw = os.getenv("CRIS_API_PW")
cris_api_baseurl = os.getenv("CRIS_API_ENDPOINT")
cris_api_url = 'https://' + cris_api_user + ':' + cris_api_pw + '@' + cris_api_baseurl
outfile = os.getenv("OUTFILE", 'oa_matches_cth.tsv')
chalmers_oa_id = os.getenv("OA_ORG_ID") # Chalmers Open Alex organization ID (we should probably also match ROR and/or org name?)
scopus_endpoint = os.getenv("SCOPUS_API_ENDPOINT")
scopus_apikey = os.getenv("SCOPUS_API_KEY")
scopus_insttoken = os.getenv("SCOPUS_INSTTOKEN")

def scopus_citation_count(scopus_eid):
    scopus_citation_count = '0'
    scopus_id = scopus_eid
    scopus_headers = {'Accept': 'application/json', 'X-ELS-APIKey': scopus_apikey, 'X-ELS-Insttoken': scopus_insttoken, 'X-Els-ResourceVersion': 'XOCS'}
    scopus_url = "http://api.elsevier.com/content/search/scopus?query=EID(" + scopus_id + ")&field=citedby-count"
    try:
        scopus_data = requests.get(url=scopus_url, headers=scopus_headers).text
        scopus_json = json.loads(scopus_data)
        if 'search-results' in scopus_json and 'entry' in scopus_json['search-results'] and len(scopus_json['search-results']['entry']) > 0:
            entry = scopus_json['search-results']['entry'][0]
            if 'citedby-count' in entry:
                print(f"Scopus citation count for Scopus ID {scopus_id} is {entry['citedby-count']}")   
                scopus_citation_count = str(entry['citedby-count'])
    except Exception as e:
        print(f"Error querying Scopus for Scopus ID {scopus_id}: {e}")
    return scopus_citation_count

def bip_scores(doi):
    bib_scores_values = {'cc': '0', 'attrank': '0', 'pagerank': '0'}
    bc_headers = {'Accept': 'application/json'}
    bc_doi = doi.replace('/', '%2F')
    bc_url = "https://bip-api.imsi.athenarc.gr/paper/scores/" + bc_doi
    try:
        bc_data = requests.get(url=bc_url, headers=bc_headers).text
        bc_json = json.loads(bc_data)
        if 'cc' in bc_json and 'doi' in bc_json:
            bib_scores_values['cc'] = str(bc_json['cc'])
        if 'attrank' in bc_json and 'doi' in bc_json:
            bib_scores_values['attrank'] = str(bc_json['attrank'])
        if 'pagerank' in bc_json and 'doi' in bc_json:
            bib_scores_values['pagerank'] = str(bc_json['pagerank'])
    except Exception as e:
        print(f"Error querying BIP for DOI {doi}: {e}")
    return bib_scores_values

headers = {'Accept': 'application/json'}

# Add headers to outfile
with open(outfile, 'a') as outfile_tsv:
    outfile_tsv.write("CRIS_ID\tTitle\tYear\tPublicationType\tDOI\tPMID\tOA_ID\tScopus_EID\tChalmers_Affiliation\tOA_Citation_Count\tScopus_Citation_Count\tBIP_CC\tBIP_Attrank\tBIP_Pagerank\tMatch_Type\n")

for i in range(1000):
    cris_url = (
        cris_api_url
        + "?query=_exists_%3AValidatedBy"
        + "%20AND%20IsDraft%3Afalse"
        + "%20AND%20IsDeleted%3Afalse"
        + "%20AND%20!_exists_%3AIsReplacedById"
        + "%20AND%20Year%3A%5B" + str(start_year) + "%20TO%20*%5D"
        + "%20AND%20("
            + "PublicationType.NameEng%3A%22Journal%20Article%22"
            + "%20OR%20PublicationType.NameEng%3A%22Paper%20in%20proceeding%22"
            + "%20OR%20PublicationType.NameEng%3A%22Review%22"
            + "%20OR%20PublicationType.NameEng%3A%22Book%22"
            + "%20OR%20PublicationType.NameEng%3A%22scientific%20journal%22"
        + ")"
        + "&max=" + str(rows_per_query)
        + "&start=" + str(offset)
        + "&sort=Id"
        + "&sortOrder=asc"
        + "&selectedFields=Id%2CTitle%2CYear%2CIdentifierDoi%2CIdentifierPubmedId%2CIdentifierScopusId%2CPublicationType.NameEng"
    )
    try:
        cris_data = requests.get(url=cris_url, headers=headers).text
        cris_json = json.loads(cris_data)
        if cris_json['TotalCount'] > 0:
            if offset > cris_json['TotalCount']:
                print("No more publications to process, exiting.")
                exit(0)
            print("Trying to match " + str(cris_json['TotalCount']) + " publications from Chalmers CRIS with OA data, starting at offset " + str(offset))
            for publ in cris_json['Publications']:
                cit_count = '0'
                oa_matched = '0'
                doi = ''
                pmid = ''
                scopus_cit_count = '0'
                scopus_eid = ''
                pubtype = publ['PublicationType']['NameEng']

                if 'IdentifierDoi' in publ and len(publ['IdentifierDoi']) > 0:
                    # OA seem to always (?) store DOI in lowercase...
                    doi = publ['IdentifierDoi'][0].strip().lower()

                if 'IdentifierScopusId' in publ and len(publ['IdentifierScopusId']) > 0:
                    scopus_eid = '2-s2.0-' + publ['IdentifierScopusId'][0].strip()
                
                # First try using DOI
                if doi:
                    oa_query = oa_url + '?filter=doi:' + doi
                    try:
                        oa_data = requests.get(url=oa_query, headers=headers).text
                        oa_json = json.loads(oa_data)
                        if oa_json['meta']['count'] > 0:
                            oa_match += 1
                            oa_match_doi += 1
                            with open(outfile, 'a') as outfile_tsv:
                                for work in oa_json['results']:
                                    if 'cited_by_count' in work:
                                        cit_count = str(work['cited_by_count'])
                                    # If available, also get Scopus citation count for comparison
                                    if scopus_eid:
                                        print(f"Found Scopus ID {scopus_eid} for CRIS publication ID {publ['Id']}, querying Scopus for citation count")
                                        scopus_cit_count = scopus_citation_count(scopus_eid)  
                                    # Add values from OpenAIRE/BIP! if available here
                                    bib_scores = bip_scores(doi)
                                    print(f"BIP scores for DOI {doi}: CC={bib_scores['cc']}, Attrank={bib_scores['attrank']}, Pagerank={bib_scores['pagerank']}")
                                    # Check if there is a Chalmers aff in OA
                                    chalmers_aff = '0'
                                    if 'authorships' in work:
                                        for auth in work['authorships']:
                                            if 'institutions' in auth:
                                                for inst in auth['institutions']:
                                                    if inst['id'] == chalmers_oa_id:
                                                        chalmers_aff = '1'
                                    line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t{pubtype}\t{doi}\t\t{work['id']}\t{scopus_eid}\t{chalmers_aff}\t{cit_count}\t{scopus_cit_count}\t{bib_scores['cc']}\t{bib_scores['attrank']}\t{bib_scores['pagerank']}\tDOI\n"
                                    outfile_tsv.write(line)
                            print(f"DOI match found for publication ID {publ['Id']} with DOI {doi}")
                            oa_matched = '1'
                        else:
                            no_oa_match += 1
                            print(f"No OA match found for publication ID {publ['Id']} with DOI {doi}")
                    except Exception as e:
                        print(f"Error querying OA for DOI {doi}: {e}")
                # If no DOI (match), try with PMID
                if oa_matched == '0' and 'IdentifierPubmedId' in publ and len(publ['IdentifierPubmedId']) > 0:
                    pmid = publ['IdentifierPubmedId'][0].strip()
                    oa_query = oa_url + '?filter=pmid:' + pmid
                    try:
                        oa_data = requests.get(url=oa_query, headers=headers).text
                        oa_json = json.loads(oa_data)
                        if oa_json['meta']['count'] > 0:
                            oa_match += 1
                            oa_match_pmid += 1
                            with open(outfile, 'a') as outfile_tsv:
                                for work in oa_json['results']:
                                    if 'cited_by_count' in work:
                                        cit_count = str(work['cited_by_count'])
                                    # If available, also get Scopus citation count for comparison
                                    if scopus_eid:
                                        print(f"Found Scopus ID {scopus_eid} for CRIS publication ID {publ['Id']}, querying Scopus for citation count")
                                        scopus_cit_count = scopus_citation_count(scopus_eid)
                                    chalmers_aff = '0'
                                    if 'authorships' in work:
                                        for auth in work['authorships']:
                                            if 'institutions' in auth:
                                                for inst in auth['institutions']:
                                                    if inst['id'] == chalmers_oa_id:
                                                        chalmers_aff = '1'
                                    line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t{pubtype}\t\t{pmid}\t{work['id']}\t{scopus_eid}\t{chalmers_aff}\t{cit_count}\t{scopus_cit_count}\t0\t0\t0\tPMID\n"
                                    outfile_tsv.write(line)
                            print(f"PMID match found for publication ID {publ['Id']} with PMID {pmid}")
                            oa_matched = '1'
                        else:
                            no_oa_match += 1
                            print(f"No OA match found for publication ID {publ['Id']} with PMID {pmid}")
                    except Exception as e:
                        print(f"Error querying OA for PMID {pmid}: {e}")
                # If no DOI or PMID (match), try with title and pubyear (fuzzy, less reliable)
                if oa_matched == '0' and 'Title' in publ and len(publ['Title']) > 0:
                    title = publ['Title'].strip().replace(" ", "+").replace('"', "%22").replace(",", "%2C").replace(":", "%20")
                    oa_query = oa_url + '?filter=title.search:' + title + ',publication_year:' + str(publ['Year'])
                    try:
                        oa_data = requests.get(url=oa_query, headers=headers).text
                        oa_json = json.loads(oa_data)
                        if oa_json['meta']['count'] > 0:
                            oa_match += 1
                            oa_match_title += 1
                            with open(outfile, 'a') as outfile_tsv:
                                for work in oa_json['results']:
                                    if 'cited_by_count' in work:
                                        cit_count = str(work['cited_by_count'])
                                    # If available, also get Scopus citation count for comparison
                                    if scopus_eid:
                                        print(f"Found Scopus ID {scopus_eid} for CRIS publication ID {publ['Id']}, querying Scopus for citation count")
                                        scopus_cit_count = scopus_citation_count(scopus_eid)
                                    chalmers_aff = '0'
                                    if 'authorships' in work:
                                        for auth in work['authorships']:
                                            if 'institutions' in auth:
                                                for inst in auth['institutions']:
                                                    if inst['id'] == chalmers_oa_id:
                                                        chalmers_aff = '1'
                                    line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t{pubtype}\t\t\t{work['id']}\t{scopus_eid}\t{chalmers_aff}\t{cit_count}\t{scopus_cit_count}\t0\t0\t0\tTITLE\n"
                                    outfile_tsv.write(line)
                            print(f"Title match found for publication ID {publ['Id']} with title {publ['Title']}")
                            oa_matched = '1'
                        else:
                            no_oa_match += 1
                            print(f"No OA match found for publication ID {publ['Id']} with title {publ['Title']}")
                    except Exception as e:
                        print(f"Error querying OA for title {publ['Title']}: {e}")
                
                checked += 1
                if oa_matched == '0':
                    with open(outfile, 'a') as outfile_tsv:
                        line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t{pubtype}\t\t\t\t{scopus_eid}\t\t\t\tNO MATCH\n"
                        outfile_tsv.write(line)
                
                print(f"Checked {checked} publications. Matched {oa_match} in total.")
                time.sleep(0.5)  # To avoid hitting rate limits
            
            offset += rows_per_query
        else:
            print("No more publications to process.")
            break
    except Exception as e:
        print(f"Error querying CRIS: {e}")
        break

    time.sleep(1) 
exit(0)
