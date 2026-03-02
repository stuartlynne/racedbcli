
import sys
import os
import io
import json
import csv
from datetime import datetime

# read BikeReg CSV file
# return next row.
# We maintain an alias list to map names to the correct spelling, and DoB
class BikeRegCSV:

    def __init__(self, csvFileName=None, alias=None, ):
        self.csvFileName = csvFileName
        self.alias = alias
        # Load aliases from catmap/bikereg_aliases.json if present
        self.aliases = {}
        try:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'catmap')
            alias_path = os.path.join(base_dir, 'bikereg_aliases.json')
            if os.path.exists(alias_path):
                with open(alias_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # normalize keys to lowercase for case-insensitive matching
                    self.aliases = {(k or '').lower(): v for k, v in data.items()}
                    print(f"Loaded {len(self.aliases)} BikeReg aliases from {alias_path}", file=sys.stdout)
                else:
                    print(
                        f"Warning: BikeReg alias file is not a JSON object: {alias_path} ({type(data).__name__})",
                        file=sys.stdout,
                    )
        except Exception as e:
            print(f"Warning: failed to load BikeReg aliases: {e}", file=sys.stdout)
            self.aliases = {}
        print(f"BikeRegCSV Aliases:", file=sys.stdout)
        for k, v in self.aliases.items():
            print(f"  {k} -> {v}", file=sys.stdout)

    def check_dob(self, dob):
        try:
            dob = datetime.strptime(dob, '%m-%d-%Y').strftime('%Y-%m-%d')
            return dob
        except ValueError as e:
            pass
        try:
            dob = datetime.strptime(dob, '%Y/%m/%d').strftime('%Y-%m-%d')
            return dob
        except ValueError as e:
            pass
        return None

    def get_next(self, first_name=None, last_name=None, dob=None):

        with open(self.csvFileName, 'r', encoding='utf-8-sig', newline='') as csvfile:
            self.csvreader = csv.DictReader(csvfile)
            for i, row in enumerate(self.csvreader):
                print('----------------------', file=sys.stdout)
                print(f"Row[{i}] {row}", file=sys.stderr) 
                dob = row['Date of Birth']
                gender = row['Gender']
                if gender:
                    if gender.lower() not in ['m', 'f']:
                        row['Gender'] = None

                print(f"DOB: {dob} Gender: {row['Gender']}", file=sys.stderr)
                if dob:
                    try:
                        dob = datetime.strptime(dob, '%m-%d-%Y').strftime('%Y-%m-%d')
                    except ValueError as e:
                        dob = datetime.strptime(dob, '%m/%d/%Y').strftime('%Y-%m-%d')

                row['Date of Birth'] = dob
                lookup = f"{row['Last Name']}, {row['First Name']}, {dob}".lower()
                print(f"Registrant[{i}]: lookup {lookup} Alias check", file=sys.stdout)
                if lookup in self.aliases:
                    # Alias tuple: (last_name, first_name, dob, uci_id)
                    last_name, first_name, dob, uci_id = self.aliases[lookup]
                    row['Last Name'] = last_name
                    row['First Name'] = first_name
                    row['Date of Birth'] = dob
                    print(f"  Alias to: [{lookup}]: {last_name}, {first_name}, {dob}", file=sys.stdout)
                yield i, row
    

    



if __name__ == "__main__":
    br = BikeRegCSV(csvFileName=sys.argv[1])

    for i, row in br.get_next():
        print(f"{i}: {row}")
