#!/usr/bin/env python3

import sys
import os
import io
import json
import psycopg2
import psycopg2.extras

# This program is used to fetch membership data from the Cycling BC API so 
# that we can update the license holders in the RaceDB database.
# Specifically the Cycling BC data is provides us with the correct:
#   - UCI ID 
#   - First and Last Name
#   - Current License Number
#   - Current Team Affiliation

# The program will read an XLSX file with the first and last names of the license holders,
# and then fetch the Cycling BC membership data for each license holder which will give
# us:
#   - UCI ID
#   - Age as of the data of the download
#   - current license number
#   - current team affiliation

# We can fetch the current license holder data from the RaceDB database using the UCI ID,
# and we need to verify that the data from the Cycling BC API matches.
# If the data does not match, we need to update the RaceDB database with the new data.

# If the data does not match, we need to update the RaceDB database with the new data.
# Create an XLSX file with the updated data that can be used to update the RaceDB database
# for license holders that need to be updated.

# 



# Class to connect to the database
# Get license holder data using the UCI ID
#
class RaceDBSQL:

    def __init__(self, host=None):
        # Connect to PostgreSQL database

        self.host = host.removeprefix("https://").removeprefix("http://").split(":")[0]

        print(f"=== Connecting to database on {self.host}", file=sys.stdout)
        conn = psycopg2.connect(
            dbname="racedb",
            user="postgres",
            password="5wHYUQ9qmttpq58EV4EG",
            host=self.host,
            port="5432"
        )
        self.conn = conn
        self.cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.debug = False

    def log_debug(self, message):
        if self.debug:
            print(message, file=sys.stderr)

    def log_sql(self, query, params, debug=True):
        """Logs the fully expanded SQL query with parameters."""
        expanded_query = query % tuple(map(lambda x: f"'{x}'" if isinstance(x, str) else str(x), params)) if params else query
        if debug:
                self.log_debug(f"Executing SQL: {expanded_query}")


    def cur_execute(self, msg, query, params, debug=True):
        """Executes a query with parameters and logs the expanded query."""
        self.log_debug(msg)
        self.log_sql(query, params, debug=debug)
        self.cur.execute(query, params)

    def find_uci_id(self, uci_id=None):
        try:
            # Connect to PostgreSQL database
            #conn, cur = connect_db(host)
            uci_id_query = "SELECT id, last_name, first_name, license_code, date_of_birth, gender, uci_id FROM core_licenseholder WHERE LOWER(uci_id) = LOWER(%s);"
            self.cur_execute(f'Find licenseholder by uciid {uci_id}', uci_id_query, (uci_id,), debug=self.debug)
            licenseholder = self.cur.fetchone()
            if licenseholder:
                print(f"SQL License Holder found: {licenseholder}", file=sys.stdout)
                return licenseholder
            print(f"No licenseholder found for {uci_id}.", file=sys.stdout)
            return None
            
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
        return None

    def find_teams(self, first_name, last_name, license_code):
        print(f"find_teams: {first_name} {last_name} {license_code}", file=sys.stdout)
        try:
            #SELECT lh.id, lh.last_name, lh.first_name, d.name AS discipline, t.name AS team
            query = """
                SELECT d.name AS discipline, t.name AS team
                FROM core_licenseholder lh
                LEFT JOIN core_teamhint th ON lh.id = th.license_holder_id
                LEFT JOIN core_discipline d ON th.discipline_id = d.id
                LEFT JOIN core_team t ON th.team_id = t.id
                WHERE lh.last_name ILIKE %s AND lh.first_name ILIKE %s and lh.license_code ILIKE %s;
            """
            
            self.cur_execute(f"Find disciplines/teams for {last_name}, {first_name}", query, (last_name, first_name, license_code), debug=self.debug)
            results = self.cur.fetchall()
            
            return results

        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
        return None


    def find_jan01(self, first_name=None, last_name=None):
        try:
            # Connect to PostgreSQL database
            #conn, cur = connect_db(host)
            jan01 = "SELECT id, last_name, first_name, license_code, date_of_birth, gender, uci_id FROM core_licenseholder WHERE TO_CHAR(date_of_birth, 'MM-DD') = '01-01';"
            self.cur_execute(f'Find licenseholder by with January 1 DoB', jan01, (), debug=self.debug)
            licenseholders = self.cur.fetchall()
            #print(f"License Holders found: {licenseholders}", file=sys.stdout)
            return licenseholders
            
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
        return None
 
    def find_name(self, first_name=None, last_name=None):
        try:
            # Connect to PostgreSQL database
            #conn, cur = connect_db(host)
            uci_id_query = "SELECT id, last_name, first_name, license_code, date_of_birth, gender, uci_id FROM core_licenseholder WHERE LOWER(first_name) = LOWER(%s) AND LOWER(last_name) = LOWER(%s);"
            self.cur_execute(f'Find licenseholder by names {last_name}, {first_name}', uci_id_query, (first_name, last_name,), debug=self.debug)
            licenseholders = self.cur.fetchmany()
            print(f"find_name: License Holders found: {licenseholders}", file=sys.stderr)
            return licenseholders
            
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
        return None
 
    def find_name_dob(self, first_name=None, last_name=None, dob=None):
        try:
            # Connect to PostgreSQL database
            #conn, cur = connect_db(host)
            uci_id_query = """
                SELECT id, last_name, first_name, license_code, date_of_birth, gender, uci_id FROM core_licenseholder 
                WHERE LOWER(first_name) = LOWER(%s) AND LOWER(last_name) = LOWER(%s) and date_of_birth = %s;
            """
            self.cur_execute(f'Find licenseholder by names {last_name}, {first_name} {dob}', uci_id_query, (first_name, last_name, dob), debug=self.debug)
            licenseholders = self.cur.fetchmany()
            print(f"find_name_dob: License Holders found: {licenseholders}", file=sys.stderr)
            return licenseholders
            
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
        return None


    def find_competition(self, name=None, date=None):
        """Find a competition by exact name and/or start_date.

        Returns a dict (id, name, long_name, start_date, category_format_id) or None.
        """
        print(f"find_competition: {name} {date}", file=sys.stdout)
        try:
            if name and date:
                competition_query = (
                    "SELECT id, name, long_name, start_date, category_format_id "
                    "FROM core_competition WHERE name = %s AND start_date = %s;"
                )
                self.cur_execute(
                    f"Find competition by name/date {name} {date}",
                    competition_query,
                    (name, date),
                    debug=self.debug,
                )
            elif name:
                competition_query = (
                    "SELECT id, name, long_name, start_date, category_format_id "
                    "FROM core_competition WHERE name = %s;"
                )
                self.cur_execute(
                    f"Find competition by name {name}", competition_query, (name,), debug=self.debug
                )
            elif date:
                competition_query = (
                    "SELECT id, name, long_name, start_date, category_format_id "
                    "FROM core_competition WHERE start_date = %s;"
                )
                self.cur_execute(
                    f"Find competition by date {date}", competition_query, (date,), debug=self.debug
                )
            else:
                print("find_competition requires name and/or date", file=sys.stderr)
                return None

            competition = self.cur.fetchone()
            if not competition:
                print(f"No competition found for {name or date}.", file=sys.stderr)
                return None
            return competition

        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
            return None

    def find_numberset(self, numberset=None):
        print(f"find_numberset: {numberset}", file=sys.stdout)
        try:
            # Connect to PostgreSQL database
            numberset_query = "SELECT id, name, description, sponsor FROM core_numberset WHERE name = %s;"
            self.cur_execute(f'Find numbset by name {numberset}', numberset_query, (numberset,), debug=True)
            numberset = self.cur.fetchone()
            if not numberset:
                print(f"No numberset found for {numberset}.", file=sys.stderr)
            return numberset
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stderr)
        return None

    # --- Categories / CategoryFormats ---
    def find_category_format(self, name):
        """Find a core_categoryformat by name (case-insensitive). Returns dict or None."""
        try:
            query = "SELECT id, name, description FROM core_categoryformat WHERE name ILIKE %s;"
            self.cur_execute(
                f"Find category format by name {name}", query, (name,), debug=self.debug
            )
            return self.cur.fetchone()
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stderr)
        return None

    def find_category_format_by_id(self, fmt_id):
        """Find a core_categoryformat by id. Returns dict or None."""
        try:
            query = "SELECT id, name, description FROM core_categoryformat WHERE id = %s;"
            self.cur_execute(
                f"Find category format by id {fmt_id}", query, (fmt_id,), debug=self.debug
            )
            return self.cur.fetchone()
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stderr)
        return None

    def find_categories_for_format_id(self, format_id):
        """Return list of categories (code, gender, description) for a format_id."""
        try:
            query = (
                "SELECT code, gender, description FROM core_category "
                "WHERE format_id = %s ORDER BY sequence, code;"
            )
            self.cur_execute(
                f"Find categories for format_id {format_id}", query, (format_id,), debug=self.debug
            )
            return self.cur.fetchall()
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stderr)
        return []

    def find_categories_for_format_name(self, format_name):
        """Find a category format by name, then return its categories.

        Returns tuple (format_record, categories).
        """
        fmt = self.find_category_format(format_name)
        if not fmt:
            return None, []
        fmt_id = fmt["id"] if isinstance(fmt, dict) else fmt[0]
        cats = self.find_categories_for_format_id(fmt_id)
        return fmt, cats

    def find_competition_categories(self, name=None, date=None):
        """Find categories for a competition identified by name and/or date.

        Returns tuple (competition_record, categories_list). If not found, returns (None, []).
        """
        comp = self.find_competition(name=name, date=date)
        if not comp:
            return None, []
        # comp is a dict (RealDictCursor).
        fmt_id = comp.get("category_format_id") if isinstance(comp, dict) else comp[4]
        cats = self.find_categories_for_format_id(fmt_id)
        return comp, cats
  

    


if __name__ == "__main__":
    racedb = RaceDBSQL("localhost")
    #licenseholder = racedb.find_uci_id(uci_id=1234567890)
    #licenseholder = racedb.find_name_dob(first_name="John", last_name="Doe", dob="1970-01-01")
    for first_name, last_name, dob in [
            ("Albert", "Chan", "1962-08-08"),
            ("Albert", "Chan", None),
            ("Brett", "Boniface", None),
            ("brett", "Boniface", None),]:
        print(f"Finding license holder for {first_name} {last_name} {dob} ", file=sys.stdout)
        if dob:
            licenseholders = racedb.find_name_dob(first_name=first_name, last_name=last_name, dob=dob)
        else:
            licenseholders = racedb.find_name(first_name=first_name, last_name=last_name)
    # Test: find categories by CategoryFormat name
    fmt_name = "lmcx2024"
    print(f"Finding categories for CategoryFormat '{fmt_name}'", file=sys.stdout)
    fmt, categories = racedb.find_categories_for_format_name(fmt_name)
    if not fmt:
        print(f"CategoryFormat '{fmt_name}' not found.", file=sys.stdout)
    else:
        print(f"CategoryFormat found: {fmt}", file=sys.stdout)
        for c in categories:
            code = c.get("code") if isinstance(c, dict) else c[0]
            gender = c.get("gender") if isinstance(c, dict) else c[1]
            desc = c.get("description") if isinstance(c, dict) else c[2]
            print(f"  {code}\t{gender}\t{desc}", file=sys.stdout)
        print(f"License Holders found: {licenseholders}", file=sys.stdout)

    # Test: find competition categories by date
    comp_date = "2018-11-11"
    print(f"Finding competition categories for date {comp_date}", file=sys.stdout)
    comp, cats = racedb.find_competition_categories(date=comp_date)
    if not comp:
        print(f"No competition found for date {comp_date}.", file=sys.stdout)
    else:
        print(f"Competition found: {comp}", file=sys.stdout)
        for c in cats:
            code = c.get("code") if isinstance(c, dict) else c[0]
            gender = c.get("gender") if isinstance(c, dict) else c[1]
            desc = c.get("description") if isinstance(c, dict) else c[2]
            print(f"  {code}\t{gender}\t{desc}", file=sys.stdout)

    sys.exit(0)
