
import sys
import argparse
import psycopg2

def log_debug(message):
    print(message, file=sys.stderr)

def log_sql(query, params, debug=True):
    """Logs the fully expanded SQL query with parameters."""
    expanded_query = query % tuple(map(lambda x: f"'{x}'" if isinstance(x, str) else str(x), params)) if params else query
    if debug:
            log_debug(f"Executing SQL: {expanded_query}")


def cur_execute(msg, cur, query, params, debug=True):
    """Executes a query with parameters and logs the expanded query."""
    log_debug(msg)
    log_sql(query, params, debug=debug)
    cur.execute(query, params)

def connect_db(host):
    # Connect to PostgreSQL database
    conn = psycopg2.connect(
        dbname="racedb",
        user="postgres",
        password="5wHYUQ9qmttpq58EV4EG",
        host=host,
        port="5432"
    )
    return conn.cursor()

def find_numberset(host, numbeset=None):
    try:
        # Connect to PostgreSQL database
        cur = connect_db(host)
        numberset_query = "SELECT id, name, description, sponsor FROM core_numberset WHERE name = %s;"
        cur_execute(f'Find numbset by name {numberset}', cur, numberset_query, (numberset,), debug=True)
        numberset = cur.fetchone()
        if not numberset:
             print(f"No numberset found for {numberset}.", file=sys.stderr)
             return
        numberset_id, numberset_name, numberset_description, numberset_sponsor = competition
        print(f"Competition found: {competition}", file=sys.stderr)
        

    except psycopg2.DatabaseError as error:
        print(f"Database error: {error}", file=sys.stderr)
    return conn, cur, numberset_id, numberset_name, numberset_description, numberset_sponsor

# Query to find the competition based on date or name
def find_competition(host, name=None, date=None):
    try:
        # Connect to PostgreSQL database
        cur = connect_db(host)

        if name:
            competition_query = "SELECT id, name, long_name FROM core_competition WHERE name = %s;"
            cur_execute(f'Find competition by name {name}', cur, competition_query,  (name,), debug=False)
        else:
            competition_query = "SELECT id, name, long_name FROM core_competition WHERE start_date = %s;"
            cur_execute(f'Find competition by date {date}', cur, competition_query, (date,), debug=True)
        
        competition = cur.fetchone()
        if not competition:
             print(f"No competition found for {name or date}.", file=sys.stderr)
             return
        competition_id, competition_name, competition_long_name = competition
        print(f"Competition found: {competition}", file=sys.stderr)

    except psycopg2.DatabaseError as error:
        print(f"Database error: {error}", file=sys.stderr)
    return conn, cur, competition_id, competition_name, competition_long_name

