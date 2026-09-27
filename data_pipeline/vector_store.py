"""
    Vector Store builder
    This will loads PubMed/ FDA/Ethics text files, splits them into chunks, embed them with
    the local embedding model or openai model and then index them in FAISS. The resulting
    retrievers are what the Guild's specialist agent query at run time.
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from data_pipeline.paths import data_paths


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                     Function Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def create_vector_store(folder_path : str , embedding_model , store_name : str):
    """
        Loads documents from a folder, splits them and creates a FAISS vector store.
    """
    print(f"------------Creating {store_name} VectorStore----------------")
    loader = DirectoryLoader(folder_path , glob="**/*.txt" , loader_cls=TextLoader , show_progress = True)
    documents = loader.load()

    if not documents:
        print(f"No Documents found in {folder_path}")
        return None, 0 , 0

    text_splitter = RecursiveCharacterTextSplitter(chunk_size = 1000 , chunk_overlap = 100)
    texts = text_splitter.split_documents(documents)

    print(f"Loaded {len(documents)} documents, split into {len(texts)} chunks.")
    print("Generating embeddings and indexing into FAISS... (This may take a moment)")
    db = FAISS.from_documents(texts, embedding_model)
    print(f"{store_name} Vector Store created successfully.")
    return db, len(documents), len(texts)


def create_retrievers(embedding_model , mimic_db_path : str) -> dict:
    """
        Builds all three FAISS retrievers and bundles them with the MIMIC db path.
    """
    pubmed_db, _, _ = create_vector_store(data_paths["pubmed"], embedding_model, "PubMed")
    fda_db, _, _ = create_vector_store(data_paths["fda"], embedding_model, "FDA")
    ethics_db, _, _ = create_vector_store(data_paths["ethics"], embedding_model, "Ethics")

    return {
        "pubmed_retriever": pubmed_db.as_retriever(search_kwargs={"k": 3}),
        "fda_retriever": fda_db.as_retriever(search_kwargs={"k": 3}),
        "ethics_retriever": ethics_db.as_retriever(search_kwargs={"k": 2}),
        "mimic_db_path": mimic_db_path,
    }


