import os

from data_pipeline.fda_loader import download_and_extract_text_from_pdf
from data_pipeline.paths import data_paths

url = "https://www.fda.gov/media/168475/download"

output_path = os.path.join(
    data_paths["fda"],
    "fda_diabetes_guidance.pdf"
)

print("Output path:", output_path)

success = download_and_extract_text_from_pdf(
    url,
    output_path
)

print("FDA download success:", success)

if os.path.exists(output_path):
    print("PDF exists:", output_path)
else:
    print("PDF was NOT created.")
