"""
    Environment configuration
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

import os 
from dotenv import load_dotenv

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                       Logic Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def load_environment() -> None:
    """
        Load .env and configure LangSmith project
    """
    load_dotenv()

    os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")
    os.environ['LANGCHAIN_API_KEY'] = os.getenv("LANGCHAIN_API_KEY")
    os.environ['ENTREZ_EMAIL'] = os.getenv("ENTREZ_EMAIL")

    if "LANGCHAIN_API_KEY" not in os.environ or "ENTREZ_EMAIL" not in os.environ:
        print("Required environment variable not set. Please set them in .env file")
    else:
        print("Environment variables loaded successfully.")

    os.environ["LANGCHAIN_PROJECT"] = "AI_Clinical_Trials_Architect"

    print(f"Langsmith tracing is configured for project '{os.environ['LANGCHAIN_PROJECT']}'.")