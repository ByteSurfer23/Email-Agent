import tempfile
from pdf_parser import extract_structured_tables
from db import save_pdf_record

@tool 
def process_uploaded_pdf(uploaded_file):
    """
    Processes a health report PDF uploaded via Streamlit file_uploader.

    Parameters
    ----------
    uploaded_file : UploadedFile
        File object returned from Streamlit uploader

    Returns
    -------
    tuple
        (success, message, data)
    """

    if uploaded_file is None:
        return False, "No file provided", None

    file_name = uploaded_file.name
    file_bytes = uploaded_file.read()

    # create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        temp_path = tmp_file.name

    data = extract_structured_tables(temp_path)

    if not data:
        return False, "Could not extract data from PDF", None

    success, message = save_pdf_record(
        file_name=file_name,
        data=data
    )

    return success, message, data