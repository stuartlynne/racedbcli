
import sys
import os
import io
import json
import csv
from datetime import datetime

BikeReg_Aliases = { 
    'brown, matthew, 1969-04-17': ('brown', 'matt', '1969-04-17', None),
    'martin, rich, 1972-03-17': ('martin', 'richard', '1972-03-17', None),
    'mallie, johannes, 1987-10-20': ('mallie', 'johannes daniel', '1987-10-20', None),
    'morin, ben, 2007-08-27': ('morin', 'ben', '2007-08-27', '00000000000'),
    #'grund, sebastian, 2009-08-23': ('grund', 'sebastain', '2009-08-23', '00000000000'), 
    "flower, thomas, 1981-05-09": ('flower', 'tom', '1981-05-09', '00000000000'),
    "mousseau, steve, 1984-11-28": ('mousseau', 'steven', '1984-11-28', '00000000000'),
    "timmer, alex, 1989-12-18": ('timmer', 'alexander', '1989-12-18', '00000000000'),
    "hickling, cam, 2003-05-12": ('hickling', 'cameron', '2003-05-12', '00000000000'),
    "treen, gordie, 2008-11-02": ('treen', 'gordon', '2008-11-02', '00000000000'),
    "patterson, cole, 1987-07-06": ('patterson', 'cole', '1995-07-06', '00000000000'),
    "davsion, james r, 1972-04-22": ('davison', 'james r', '1972-04-22', '00000000000'),
    "rubuliak, jenni, 1973-04-24": ('rubuliak', 'jen', '1973-04-24', '00000000000'),
    "ben shooshan, noam, 2009-02-13": ('ben-shooshan', 'noam', '2009-02-13', '00000000000'),
    "ben shooshan, shaqed, 2014-03-02": ('ben-shooshan', 'shaqed', '2014-03-02', '00000000000'),
    "imlach, brittany, 1989-03-07": ('imlach', 'brittany georgia', '1989-03-07', '00000000000'),
    "kelley, xavier, 1975-04-28": ('kelley', 'xavier', '2008-02-27', '00000000000'),
    "ramirez, marklouie, 2004-09-27": ('ramirez', 'mark louie', '2004-09-27', '00000000000'),
    "ivany, carsten ivany, 1981-01-25": ('ivany', 'carsten', '1981-01-25', '00000000000'),
    "hutchinson, alexander, 1993-06-20": ('hutchinson', 'alex', '1993-06-20', '00000000000'),
    "o'mahony, david, 1981-04-15": ("o'mahony", 'dave', '1981-04-15', '00000000000'),
    "murison, alex, 1992-02-04": ('murison', 'alexander', '1992-02-04', '00000000000'),
    "wood, dan, 1972-10-20": ('wood', 'daniel', '1972-10-20', ''),


}

# read BikeReg CSV file
# return next row.
# We maintain an alias list to map names to the correct spelling, and DoB
class BikeRegCSV:

    def __init__(self, csvFileName=None, alias=None, ):
        self.csvFileName = csvFileName
        self.alias = alias

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
                print(f"Registrant[{i}]: {lookup} ", file=sys.stdout)
                if lookup in BikeReg_Aliases:
                    last_name, first_name, dob, uci_id = BikeReg_Aliases[lookup]
                    row['Last Name'] = last_name
                    row['First Name'] = first_name
                    row['Date of Birth'] = dob
                    print(f"  Alias to: [{lookup}]: {last_name}, {first_name}, {dob}", file=sys.stdout)
                yield i, row
    

    



if __name__ == "__main__":
    br = BikeRegCSV(csvFileName=sys.argv[1])

    for i, row in br.get_next():
        print(f"{i}: {row}")

