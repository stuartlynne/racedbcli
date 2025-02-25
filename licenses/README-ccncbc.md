# CCN Cycling BC Membership

## Introduction

RaceDB stores participants as "license holders". These are people who have a license to race.

Each license holder needs to have:

Required:
- first and last name
- Date of Birth

Optional and Unique:
- a unique license number 
- a unique UCI ID


Since multiple license holders can have the same name, 
we need to use either the license number or UCI ID to uniquely identify them.


## Cycling BC Membership Data

What we get from them:
- first and last name
- uci id
- team

Bizarrely missing is the Cycling BC License number!


## ccncbc.py

For each member of the Cycling BC membership list we get:
- first and last name
- uci id

For each first-last name pair I fetch the license holder data 
using the CCN/Cycling BC membership online lookup 
(which can provide multiple records, e.g. there are two Albert Chan records for two different people.)

That gets us the *license number*.

From there I query RaceDB using UCI ID to see if we have a record. If that fails I query for (again possibly multiple) first-last names.

If we find a record in RaceDB that gets us the *DoB*, *gender* and what RaceDB thinks is the *license number*.

Putting that all together:
- we have missing license holders
- found but incorrect license number
- found but incorrect uci id (mostly missing)

The incorrect fields are easy. But the missing license holders are more difficult because we have no clue for gender and only a vague idea of DoB based on age. For these I am adding them to RaceDB with gender as M and DoB {2025-age}-01-01, and a note="FIX AGE AND GENDER".

It should be relatively easy to fix these at registration.

I have also put in issue for RaceDB to have a new LicenseHolder import based on UCI ID that will allow changing DoB, gender etc. So our prereg scripts can compare DoB and Gender from pre-reg to RaceDB and update if required.

Updating License Holder data is done directly. No intermediate files or need to do manual upload in RaceDB.

## Example of License Holder with fake DoB and Gender
Example License Holder data:

[Licence Holder] (./lh1.png)
[Licence Holder Edit] (./lh2.png)

The script generates an in-memory xlsx file and then connects to RaceDB to do the license holder import with appropriate options.

```
Processing: Justin Harrington
Find licenseholder by uciid 10161077776
No licenseholder found for 10161077776.
Find licenseholder by names Harrington, Justin
Checking: Justin Harrington 10161077776 using name not found
  Person: {'first_name': 'Justin', 'last_name': 'Harrington', 'age': 15, 'membership': 'Cycling BC Annual Membership / License 2025', 'uci_id': '10161077776', 'license_number': 'PR2311079', 'license_type': 'Provincial RACE License (All Disciplines)', 'licenses': ['Downhill :: Youth :: Under 17 :: Sport'], 'team': 'Escape Velocity / Devo Club'}
  License Holder: None
No license holder found for Justin Harrington.
--------------------------------------------
=== Logging in to http://localhost:9080 as super
=== GET to login page: http://localhost:9080/RACEDB/Login/?next=/RaceDB/
=== POST to login: http://localhost:9080/RACEDB/Login/
=== GET to upload form page: http://localhost:9080/RaceDB/LicenseHolders/LicenseHoldersImportExcel/
Upload form action: http://localhost:9080/RaceDB/LicenseHolders/LicenseHoldersImportExcel/
=== POST file to: http://localhost:9080/RaceDB/LicenseHolders/LicenseHoldersImportExcel/ data: {'set_team_all_disciplines': 'on', 'update_license_codes': 'on', 'ok-submit': 'OK', 'csrfmiddlewaretoken': ('NFgw7n6HKSFQXsrEZKn9Vf8SOxj26ZmpniQ0hR2OhvToGcKXgxJiJDj53bSEL7Wp',)}
=== Upload Result Table ===
 | Row | Message
 |  | Reading sheet "Sheet1"
 |  | Header Row:
 |  | 1. Last Name --> last_name
 |  | 2. First Name --> first_name
 |  | 3. License --> license_code
 |  | 4. UCI ID --> uci_id
 |  | 5. DOB --> date_of_birth
 |  | 6. Gender --> gender
 |  | 7. Team --> team
 |  | 8. Note --> note
 |  | 9. ****Comments (Ignored)
 |  |
 | 2 | Added:PR2311079: last_name="Harrington", first_name="Justin", gender=Men, date_of_birth=2010-01-01, uci_id="10161077776", license_code="PR2311079", suspended=False, active=True, eligible=True, note="FIX AGE AND GENDER!"
 |  |
 |  | Added:1
 |  | Initialization in: 0:00:00.175565
 |  |

```
