"""
    LLM Foundry
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()
import os 
_llm_config = None 
openai_api = os.getenv("OPENAI_API_KEY")


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                     Function Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚


def get_llm_config() -> dict:
    """
        Lazy build and cache the model suite (singleton)
    """
    global _llm_config
    if _llm_config is not None:
        return _llm_config

    llm_config = {
        "planner" : ChatOpenAI(model="gpt-4o-mini" , api_key=openai_api , temperature=0.0),
        "drafter" : ChatOpenAI(model="gpt-4o-mini" , api_key=openai_api , temperature=0.0),
        "sql_coder" : ChatOpenAI(model="gpt-4o-mini" , api_key=openai_api , temperature=0.0),
        "director" : ChatOpenAI(model="gpt-4o-mini" , api_key=openai_api , temperature=0.0),
        "embedding_model" : OpenAIEmbeddings(model="text-embedding-3-small" , api_key=openai_api)
    }

    print("LLM Clients configured.")
    _llm_config = llm_config

    return _llm_config