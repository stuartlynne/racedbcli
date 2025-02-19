# RaceDB CLI Support

## CLI Programs
- uucid.py - merge ccn data and existing RaceDB data to update and/or create license holder data
- numberset.py - download or upload a number set xlsx
- template.py - download a competition as a template for a new competition

- licenseholders.py - upload license holder xlsx file to update the database
- prereg.py - upload preregistration xlsx file to update a competition

- competition.py - create a new competition from a previous one used as a template

## SQL Libraries
- findcompetition.py - find a competition by name or date using SQL
- findnumberset.py - find a numberset by name or date using SQL

## Request Libraries
- login.py - login to the server, return requests session
- download.py - download data from the server
- upload.py - upload data to the server

## License Holder Update
- membership.xlsx - first name, last name, uci id, team
- connects to CCN to get age, and license number
- connects to racedb to get existing DoB and gender
- updates racedb with to update license number or uci id as needed
- creates a new license holder if not found

N.b. We do not get gender or DoB from CCN, so if creating a new license holder, we set the DoB to {2025-age}-01-01, gender to M and note to "FIX DOB AND GENDER".


## Workflow
Pre-event Workflow becomes:
- create event with new date and name, competition.py
- get pre-registration
- create license holder update and pre-reg xlsx files
- upload license holder, licenseholders.py
- upload pre-reg, prereg.py
- create start lists and crossmgr files, startlists.py
- sync start lists and crossmgr files to results site, awsssh sync
- verify that competition has been created with correct date, name and has pre-reg data

All of that can be done with a Makefile once pre-registration file has been downloaded.

Event workflow for each race:
- create start lists and crossmgr files, startlists.py
- sync start lists, crossmgr files and previous race results (if any) to results site, aswssh sync
- time race with crossmgr
- if last race, sync last results to results site



