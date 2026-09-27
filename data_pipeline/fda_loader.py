"""
    FDA guideLine downloder.
    It will downloads a PDF from the FDA website, saves the raw PDF and extracts its
    text to a .txt file so it can indexed by the Regulatory Specialist;s vector store.
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

import io 
import os 
import requests
from pypdf import PdfReader

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                     Function Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def download_and_extract_text_from_pdf(url : str , output_path : str) -> bool:
    print(f"Downloading FDA Guidelines : {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()

        with open(output_path , "wb") as f:
            f.write(response.content)
        print(f"Successfully downloaded and saved to {output_path}")

        reader = PdfReader(io.BytesIO(response.content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n\n"

        txt_output_path = os.path.splitext(output_path)[0] + ".txt"
        with open(txt_output_path , "w") as f:
            f.write(text)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error Downloading file : {e}")
        return False