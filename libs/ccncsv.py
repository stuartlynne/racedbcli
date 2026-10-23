
import sys
import os
import io
import json
import csv
from datetime import datetime

def _decode_csv_bytes(data: bytes) -> str:
    """Decode CCN CSV bytes robustly.
    Try utf-8-sig/utf-8 first, then cp1252 and latin-1 to handle names with accents.
    """
    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']
    last_err = None
    for enc in encodings:
        try:
            return data.decode(enc)
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise last_err or UnicodeDecodeError('utf-8', data, 0, 1, 'unable to decode')


def _sniff_dialect(sample_text: str) -> csv.Dialect:
    """Sniff CSV/TSV dialect for CCN exports. Fallback to comma/tab heuristic."""
    sniffer = csv.Sniffer()
    sample = sample_text[:8192]
    try:
        dialect = sniffer.sniff(sample, delimiters=",\t;")
        return dialect
    except Exception:
        c_comma = sample.count(',')
        c_tab = sample.count('\t')
        delim = '\t' if c_tab > c_comma else ','
        Fallback = type(
            'FallbackDialect',
            (csv.Dialect,),
            dict(
                delimiter=delim,
                quotechar='"',
                escapechar=None,
                doublequote=True,
                skipinitialspace=False,
                lineterminator='\n',
                quoting=csv.QUOTE_MINIMAL,
            ),
        )
        return Fallback()


def _is_ccn_trailer_row(row: dict) -> bool:
    """Heuristically detect CCN trailer/summary rows.
    Looks at the first non-empty cell and matches common trailer prefixes.
    """
    values = [v for v in row.values() if v]
    if not values:
        # an all-empty row commonly appears in tails; keep scanning but do not treat as data
        return False
    first_cell = str(values[0]).strip().lower()
    prefixes = (
        'complete registrations for',
        'filters',
        'event:',
        'standalone:',
        'statuses:',
        'without_issued_required_membership_only:',
        'without issued required membership only:',
    )
    if any(first_cell.startswith(p) for p in prefixes):
        return True
    # Also treat ctime-like footer lines as trailer, e.g., "Thu Sep 11 18:48:48 (develop)"
    # Start with weekday abbrev followed by month abbrev
    import re
    if re.match(r"^[a-z]{3} [a-z]{3} ", first_cell):
        return True
    # Lines containing 'generated at' are part of the trailer header
    if 'generated at ' in first_cell:
        return True
    return False

# read CCN CSV file
# return next row.
# We maintain an alias list to map names to the correct spelling, and DoB
class CCNRegCSV:

    def __init__(self, csvFileName=None, alias=None, ):
        self.csvFileName = csvFileName
        self.alias = alias

    def check_dob(self, dob):
        try:
            dob = datetime.strptime(dob, '%Y/%m/%d').strftime('%Y-%m-%d')
            return dob
        except ValueError as e:
            pass
        try:
            dob = datetime.strptime(dob, '%m-%d-%Y').strftime('%Y-%m-%d')
            return dob
        except ValueError as e:
            pass
        return None

    def get_next(self, first_name=None, last_name=None, dob=None):
        #Category,First Name,Last Name,Gender,Date of Birth,License,Email,Emergency Contact,Emergency Contact Phone,Medical Conditions,UCI ID
        #Cycling BC Provincial Championships,Michael,Dawson,Male,1979/09/23,BC091672,mrdwsn@gmail.com,,,,

        # Read as bytes, decode with fallbacks, sniff delimiter, and parse
        with open(self.csvFileName, 'rb') as fb:
            raw = fb.read()
        text = _decode_csv_bytes(raw)
        dialect = _sniff_dialect(text)
        self.csvreader = csv.DictReader(io.StringIO(text), dialect=dialect)
        for i, row in enumerate(self.csvreader):
                print(f"[{i}] ----------------------", file=sys.stdout)
                print(f"Row[{i}] {row}", file=sys.stderr) 

                # Skip entirely empty rows
                if not any(row.values()):
                    continue

                # Stop at CCN trailer/summary section (do not yield trailer rows)
                if _is_ccn_trailer_row(row):
                    break

                # Normalize column names across CCN variants
                # DOB may be 'DOB' or 'Date of Birth'
                dob = row.get('DOB') or row.get('Date of Birth')
                # Gender may be 'Sex' (Male/Female) or 'Gender' (M/F)
                gender = row.get('Gender') or row.get('Sex')
                if gender:
                    gl = gender.strip().lower()
                    if gl in ['male', 'm']:
                        gender = 'M'
                    elif gl in ['female', 'f']:
                        gender = 'F'
                    else:
                        gender = None
                row['Gender'] = gender

                print(f"DOB: {dob} Gender: {row['Gender']}", file=sys.stderr)
                if dob:
                    try:
                        dob = datetime.strptime(dob, '%Y-%m-%d').strftime('%Y-%m-%d')
                    except ValueError as e:
                        dob = datetime.strptime(dob, '%Y/%m/%d').strftime('%Y-%m-%d')

                # Preserve both keys for downstream usage
                row['Date of Birth'] = dob
                row['DOB'] = dob

                lookup = f"{row.get('Last Name','')}, {row.get('First Name','')}, {dob}".lower()
                print(f"Registrant[{i}]: {lookup} ", file=sys.stderr)
                #if lookup in BikeReg_Aliases:
                #    last_name, first_name, dob, uci_id = BikeReg_Aliases[lookup]
                #    row['Last Name'] = last_name
                #    row['First Name'] = first_name
                #    row['Date of Birth'] = dob
                #    print(f"  Alias to: [{lookup}]: {last_name}, {first_name}, {dob}", file=sys.stdout)
                yield i, row
    

    



if __name__ == "__main__":
    br = CCNRegCSV(csvFileName=sys.argv[1])

    for i, row in br.get_next():
        print(f"{i}: {row}")
