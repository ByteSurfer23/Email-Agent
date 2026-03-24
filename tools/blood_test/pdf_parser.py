import pdfplumber
import re
from datetime import datetime


def detect_substrate(text):
    text = text.lower()

    if "urine" in text:
        return "Urine"
    if "serum" in text:
        return "Blood"
    if "plasma" in text:
        return "Plasma"
    if "blood" in text:
        return "Blood"

    return "Unknown"


def extract_date(text):
    match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if match:
        return datetime.strptime(match.group(1), "%d/%m/%Y").strftime("%Y-%m-%d")
    return None


def parse_reference_range(ref_string):
    if not ref_string:
        return None, None

    match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)", ref_string)
    if match:
        return float(match.group(1)), float(match.group(2))

    return None, None


def is_section_header(marker, value, unit):
    if not marker:
        return True

    if value is None and not unit:
        return True

    if marker.isupper() and len(marker.split()) <= 3 and value is None:
        return True

    return False


def normalize_marker(marker):
    if not marker:
        return None

    marker = re.sub(r"\(.*?\)", "", marker)  # remove method names
    marker = marker.split("\n")[0]           # keep first line only
    marker = re.sub(r"\s+", " ", marker)     # remove extra spaces
    marker = marker.strip()

    return marker


def extract_structured_tables(file):

    structured_data = []

    with pdfplumber.open(file) as pdf:

        for page_number, page in enumerate(pdf.pages):

            page_text = page.extract_text() or ""

            substrate = detect_substrate(page_text)
            date = extract_date(page_text)

            tables = page.extract_tables()

            for table in tables:

                if not table or len(table) < 2:
                    continue

                for row in table[1:]:

                    marker = row[0] if len(row) > 0 else None
                    value = row[1] if len(row) > 1 else None
                    unit = row[2] if len(row) > 2 else None
                    reference = row[3] if len(row) > 3 else None

                    marker = marker.strip() if marker else None
                    unit = unit.strip() if unit else None
                    reference = reference.strip() if reference else None

                    try:
                        value = float(value) if value else None
                    except:
                        value = None

                    marker = normalize_marker(marker)

                    if marker and marker.lower().startswith("note"):
                        continue

                    if is_section_header(marker, value, unit):
                        continue

                    ref_min, ref_max = parse_reference_range(reference)

                    missing = []

                    if not marker:
                        missing.append("marker")
                    if value is None:
                        missing.append("value")
                    if not unit:
                        missing.append("unit")
                    if not reference:
                        missing.append("reference_range")

                    entry = {
                        "marker": marker,
                        "value": value,
                        "unit": unit,
                        "reference_range": reference,
                        "reference_min": ref_min,
                        "reference_max": ref_max,
                        "date": date,
                        "substrate": substrate,
                        "page": page_number + 1,
                        "missing_fields": missing
                    }

                    structured_data.append(entry)

    return structured_data