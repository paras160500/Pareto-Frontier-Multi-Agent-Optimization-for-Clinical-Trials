"""
    PubMed abstract downloader
    It uses Bio.Entrez to query NCBI PubMed and saves title _ abstract text files,
    which later will feed the medical researcher agent's vector store.
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

import os 
from Bio import Entrez, Medline
from data_pipeline.paths import data_paths


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                     Function Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def download_pubmed_articles(query : str , max_articles : int = 20) -> int:
    """
        Fetch abstracts from PubMed and saves them as text files. Returns count saved.
    """
    Entrez.email = os.environ.get("ENTREZ_EMAIL")
    print(f"Fetching PubMed articles for query : {query}")
    handle = Entrez.esearch(db="pubmed" , term=query , retmax = max_articles , sort = "relevance")
    record = Entrez.read(handle)
    id_list = record("IdList")
    print(f"Found {len(id_list)} article IDs.")

    print("Downloading articles...")
    handle = Entrez.efetch(db="pubmed" , id=id_list , rettype = "medline" , retmode = "text")
    records = Medline.parse(handle)

    count = 0 
    for i , record in enumerate(records):
        pmid = record.get("PMID" , "")
        title = record.get("TI" , "No Title")
        abstract = record.get("AB" , "No Abstract")

        if pmid:
            filepath = os.path.join(data_paths['pubmed'] , f"{pmid}.txt")
            with open(filepath , "w") as f:
                f.write(f"Title : {title}\n\nAbstract  {abstract}")

            print(f"[{i + 1} / {len(id_list)}] fetching PMID {pmid}... Saved to {filepath}")
            count += 1 
    return count 