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

def download_and_extract_text_from_pdf(url: str, output_path: str) -> bool:
    print(f"Downloading FDA Guidelines: {url}")

    try:
        output_dir = os.path.dirname(output_path)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.fda.gov/",
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=60,
            allow_redirects=True
        )

        print(f"FDA response status: {response.status_code}")
        print(f"FDA final URL: {response.url}")
        print(
            f"FDA content type: "
            f"{response.headers.get('Content-Type', 'unknown')}"
        )

        response.raise_for_status()

        # Make sure we actually received a PDF
        if not response.content.startswith(b"%PDF"):
            print("FDA response is not a PDF.")
            print("First 200 bytes:")
            print(response.content[:200])
            return False

        # Save PDF
        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"Successfully downloaded PDF to {output_path}")

        # Extract PDF text
        reader = PdfReader(io.BytesIO(response.content))

        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text_parts.append(page_text)

        text = "\n\n".join(text_parts)

        # Save extracted text
        txt_output_path = os.path.splitext(output_path)[0] + ".txt"

        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Extracted text saved to {txt_output_path}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"Error downloading FDA file: {e}")
        return False

    except Exception as e:
        print(f"Error processing FDA PDF: {e}")
        return False
