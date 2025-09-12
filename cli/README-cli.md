# RaceDBCLI - cli programs




## CLI Working Minimally
### template.py
Download a template for a competition from RaceDB.

Defines:
- download_template
```
sql = RaceDBSQL()
racedb = RaceDB(sql)

```


### numberset.py
Upload or download a number set from RaceDB.
   
Defines:
- upload_numberset
- download_numberset
```
sql = RaceDBSQL()
racedb = RaceDB(sql)
numberset = racedb.find_numberset(name='My Numberset')
if filepath:
    upload_numberset(sql, numbetset['id], filepath)
else:
    download_numberset(racedb, numberset['id'],) 
```

### licenseholders.py
Upload a list of license holders to RaceDB.

Defines:
- upload_licenseholders
```
sql = RaceDBSQL()
racedb = RaceDB(sql)
upload_licenseholders(sql, racedb, filename='licenseholders.xlsx')
```

### participants.py
Download a participant list for a competition from RaceDB.
```
sql = RaceDBSQL()
racedb = RaceDB(sql)
competition = racedb.find_competition(name=None, date='2024-12-12')
download_participants(sql, racedb, competition['id'], filename=None)
```

Defines:
- download_participants

### findcategories.py
Extract categories from a registration CSV (BikeReg or CCN), then create or merge a JSON label→[category, gender] map.

Modes:
- One-arg: print mapping to stdout
- Two-arg (format, CSV): `format CSV` → writes to `catmap/<format>.json`
- Two-arg (CSV, output): `CSV output.json` → writes to the given JSON path (creates if missing)

Column selection (required):
- `--bikereg` uses `Category Entered / Merchandise Ordered`
- `--ccnreg` uses `Category`

Validation (optional):
- Use `--format <name>` or `--name/--date` to load allowed category codes from RaceDB. Unknowns are prefixed with `FIX `.

Examples:
```
# Print mapping to stdout (no merge)
python cli/findcategories.py tmp/registrations.csv --bikereg

# Merge into catmap/<format>.json (creates file if missing)
python cli/findcategories.py road tmp/registrations.csv --ccnreg

# Merge/create a specific output file
python cli/findcategories.py tmp/registrations.csv tmp/catmap.json --bikereg

# With validation by competition
python cli/findcategories.py tmp/registrations.csv tmp/catmap.json --bikereg \
  --host http://localhost:8080 --name "Event Name" --date 2025-06-01
```

### competition.py
Create or replace a competition in RaceDB using a previous competition as a template.

Defines:
- create_competition_from_template
```
sql = RaceDBSQL()
racedb = RaceDB(sql)
create_competition_from_templage(sql, racedb, template_date='2024-12-12', 
    start_date='2025-12-12', new_name='My New Competition', replace=True)
```

### prereg.py
Upload a pre-registration xlsx file for a competition to RaceDB.

Defines:
- upload_prereg
```
sql = RaceDBSQL()
race = RaceDB(sql)
competition = racedb.find_competition(name=None, date='2024-12-12')
upload_prereg(sql, racedb, competition['id'], filename='prereg.xlsx')
```

### ccncbc.py
Use a CCN or Cycling BC license holder list to update RaceDB with current membership status.


---------------------------------------------------------------------------------------

## CLI Work in progress

### bikereg.py
Process a bikereg pre-registration file for a competition.


