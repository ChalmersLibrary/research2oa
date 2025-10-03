#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
import json
import sys
from dotenv import load_dotenv
import csv
from datetime import datetime
import os
import random
import string
import uuid
import configparser

# Script for matching Chalmers CRIS publication records with Open Alex contents
# Exact match with DOI and/or PMID first, then fuzzy match with title and (CRIS) publication year
# Output: CRIS Publication ID, CRIS Title, CRIS Year, CRIS DOI, CRIS PMID, Open Alex Publication ID, OA Title, OA Chalmers Affiliation (0/1), OA Reference Count, Match Type (DOI/PMID/Title/NO MATCH)
# Use .env file for configuration (see env_example)

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

# Outfile
outfile = 'oa_matches_cth.tsv'

headers = {'Accept': 'application/json'}

for i in range(500):
    cris_url = cris_api_url + "?query=_exists_%3AValidatedBy%20AND%20IsDraft%3Afalse%20AND%20IsDeleted%3Afalse%20AND%20!_exists_%3AIsReplacedById%20AND%20Year%3A%5B" + str(start_year) + "%20TO%20*%5D%20AND%20(PublicationType.NameEng%3A%22Journal%20Article%22%20OR%20PublicationType.NameEng%3A%22Paper%20in%20proceeding%22%20OR%20PublicationType.NameEng%3A%22Review%22%20%20OR%20PublicationType.NameEng%3A%22Monograph%22)&max=" + str(rows_per_query) + "&start=" + str(offset) + "&sort=Id&sortOrder=asc&selectedFields=Id%2CTitle%2CYear%2CIdentifierDoi%2CIdentifierPubmedId%2CPublicationType.NameEng"

    try:
        cris_data = requests.get(url=cris_url, headers=headers).text
        cris_json = json.loads(cris_data)
        if cris_json['TotalCount'] > 0:
            if offset > cris_json['TotalCount']:
                print("No more publications to process. Exiting")
                exit(0)
            print("Trying to match " + str(cris_json['TotalCount']) + " publications from Chalmers CRIS with OA data, starting at offset " + str(offset))
            for publ in cris_json['Publications']:
                ref_count = '0'
                oa_matched = '0'
                doi = ''
                pmid = ''
                
                # First try using DOI
                if 'IdentifierDoi' in publ and len(publ['IdentifierDoi']) > 0:
                    doi = publ['IdentifierDoi'][0].strip()
                    oa_query = oa_url + '?filter=doi:' + doi
                    try:
                        oa_data = requests.get(url=oa_query, headers=headers).text
                        oa_json = json.loads(oa_data)
                        if oa_json['meta']['count'] > 0:
                            oa_match += 1
                            oa_match_doi += 1
                            with open(outfile, 'a') as outfile_tsv:
                                for work in oa_json['results']:
                                    if 'referenced_works_count' in work:
                                        ref_count = str(work['referenced_works_count'])
                                    # Check if there is a Chalmers aff in OA
                                    chalmers_aff = '0'
                                    if 'authorships' in work:
                                        for auth in work['authorships']:
                                            if 'institutions' in auth:
                                                for inst in auth['institutions']:
                                                    if inst['id'] == 'https://openalex.org/I66862912':
                                                        chalmers_aff = '1'
                                    line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t{doi}\t\t{work['id']}\t{work['title']}\t{chalmers_aff}\t{ref_count}\tDOI\n"
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
                                    if 'referenced_works_count' in work:
                                        ref_count = str(work['referenced_works_count'])
                                    chalmers_aff = '0'
                                    if 'authorships' in work:
                                        for auth in work['authorships']:
                                            if 'institutions' in auth:
                                                for inst in auth['institutions']:
                                                    if inst['id'] == 'https://openalex.org/I66862912':
                                                        chalmers_aff = '1'
                                    line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t\t{pmid}\t{work['id']}\t{work['title']}\t{chalmers_aff}\t{ref_count}\tPMID\n"
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
                    title = publ['Title'].strip().replace(" ", "+").replace('"', "%22").replace(",", "%2C").replace(":", "%3A")
                    oa_query = oa_url + '?filter=title.search:' + title + ',publication_year:' + str(publ['Year'])
                    try:
                        oa_data = requests.get(url=oa_query, headers=headers).text
                        oa_json = json.loads(oa_data)
                        if oa_json['meta']['count'] > 0:
                            oa_match += 1
                            oa_match_title += 1
                            with open(outfile, 'a') as outfile_tsv:
                                for work in oa_json['results']:
                                    if 'referenced_works_count' in work:
                                        ref_count = str(work['referenced_works_count'])
                                    chalmers_aff = '0'
                                    if 'authorships' in work:
                                        for auth in work['authorships']:
                                            if 'institutions' in auth:
                                                for inst in auth['institutions']:
                                                    if inst['id'] == 'https://openalex.org/I66862912':
                                                        chalmers_aff = '1'
                                    line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t\t\t{work['id']}\t{work['title']}\t{chalmers_aff}\t{ref_count}\tTitle\n"
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
                        line = f"{publ['Id']}\t{publ['Title']}\t{publ['Year']}\t{doi}\t{pmid}\t\t\t0\t0\tNO MATCH\n"
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
