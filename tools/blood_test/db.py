import os
from tinydb import TinyDB, Query
from gen_hash import generate_file_hash

db = TinyDB("health_db.json")
PDF = Query()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def save_pdf_record(file_name, data):

    file_path = os.path.join(UPLOAD_FOLDER, file_name)

    # Generate hash
    file_hash = generate_file_hash(file_path)

    # Check duplicate
    existing = db.search(PDF.file_hash == file_hash)
    if existing:
        os.remove(file_path)
        return False, "PDF already exists"

    db.insert({
        "file_name": file_name,
        "file_path": file_path,
        "file_hash": file_hash,
        "parsed_data": data
    })

    return True, "PDF saved successfully"