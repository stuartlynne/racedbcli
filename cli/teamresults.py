#!/usr/bin/python3
import sys
import os
import re
import datetime
#import pandas as pd
import operator
import xlrd
from xlrd import open_workbook
import openpyxl
from openpyxl import load_workbook


from yattag import Doc, indent

##7FE57F
table_color = "#f59342"

# This is the javascript to toggle the visibility of the inner tables.
# There are two versions, one for the team riders and one for the rider events.
# In both cases when clicked:
#   - clear any existing timeout
#   - toggle the visibility of the inner table
#   - set a timeout to hide the inner table after 60 seconds
#
# The two functions are called with the teamId or eventId as the argument
# end look for the hidden-rider-row or hidden-event-row with the matching data_team or data_event attribute.
#

toggleVisibility = """
    var categoryHoverTimers = {};
    var activeId = null;
    var activeToggle = null;
    function categoryToggleVisibility(categoryId, toggleButton, toggleDisplay, toggleDesignedBy) { 
        console.log('categoryId:', categoryId); 
        console.log('toggleButton:', toggleButton);
        console.log('toggleDisplay:', toggleDisplay);
        console.log('toggleDesignedBy:', toggleDesignedBy);
        if (activeId !== null && activeId !== categoryId) {
            var rows = document.querySelectorAll(`.hidden-category-row[data_category="${activeId}"]`); 
            rows.forEach(function(row) { 
                row.style.display = "none"; 
                }); 
            activeId = null
        }
        if (activeToggle !== null && activeToggle !== toggleButton) {
            var button = document.getElementById(activeToggle);
            button.innerHTML = '+';
            activeToggle = null;
        }   
        var rows = document.querySelectorAll(`.hidden-category-row[data_category="${categoryId}"]`); 
        console.log('rows:', rows); 
        rows.forEach(function(row) { 
            row.style.display = (row.style.display === "none" || row.style.display === "") ? "table-row" : "none"; 
            }); 
        activeId = categoryId;
        activeToggle = toggleButton;
        // XXX need to track the toggle state of the button and display
        if (toggleButton && toggleButton !== null ) {
            var button = document.getElementById(toggleButton);
            button.innerHTML = (button.innerHTML === '+') ? '-' : '+';
        }
        if (toggleDisplay && toggleDisplay !== null) {
            var display = document.getElementById(toggleDisplay);
            display.innerHTML = (display.innerHTML === 'Points') ? '' : 'Points';
        }
        if (toggleDesignedBy && toggleDesignedBy !== null) {
            clearTimeout(categoryHoverTimers[toggleDesignedBy]);
            var display = document.getElementById(toggleDesignedBy);
            display.innerHTML = (display.innerHTML === 'Wimsey Timing Services') ? 'Designed by Stuart Lynne with ChatGPT, Built with CoPilot' : 'Wimsey Timing Services';
            categoryHoverTimers[toggleDesignedBy] = setTimeout(function() {
                display.innerHTML = 'Wimsey Timing Services';
                //display.innerHTML = window.innerWidth;
            }, 10000);
        }
    }
    var teamHoverTimers = {};
    function teamToggleVisibilityTimeout(teamId) { 
        console.log('teamId:', teamId); 
        var rows = document.querySelectorAll(`.hidden-rider-row[data_team="${teamId}"]`); 
        console.log('rows:', rows); 
        clearTimeout(teamHoverTimers[teamId]);
        rows.forEach(function(row) { 
            row.style.display = (row.style.display === "none" || row.style.display === "") ? "table-row" : "none"; 
            }); 
        teamHoverTimers[teamId] = setTimeout(function() {
            rows.forEach(function(row) {
                row.style.display = "none";
            });
        }, 60000);
    }
    var eventHoverTimers = {};
    function eventToggleVisibilityTimeout(eventId) { 
        console.log('eventId:', eventId); 
        var rows = document.querySelectorAll(`.hidden-event-row[data_event="${eventId}"]`); 
        console.log('rows:', rows); 
        clearTimeout(eventHoverTimers[eventId]);
        rows.forEach(function(row) { 
            row.style.display = (row.style.display === "none" || row.style.display === "") ? "table-row" : "none"; 
            }); 
        eventHoverTimers[eventId] = setTimeout(function() {
            rows.forEach(function(row) {
                row.style.display = "none";
            });
        }, 60000);
    }

"""

# Tables
#   + ---------------------
#   | Title
#   + ---------------------
#   | Categories
#   |   + ------------
#   |   | Category
#   |   |  + --------
#   |   |  | Teams
#   |   |  |  + -----
#   |   |  |  | Team
#   |   |  |  |  + ---
#   |   |  |  |  | Riders
#   |   |  |  |  |  + --
#   |   |  |  |  |  | Rider
#   |   |  |  |  |  |  + -----
#   |   |  |  |  |  |  | Events
#   |   |  |  |  |  |  |  + ----
#   |   |  |  |  |  |  |  | Event
#   |   |  |  |  |  |  |  + ----
#   |   |  |  |  |  |  |  + ----
#   |   |  |  |  |  |  |  | Event
#   |   |  |  |  |  |  + -----
#   |   |  |  |  |  + -----
#   |   |  |  |  |  + --
#   |   |  |  |  |  | Rider
#   |   |  |  + --------
#   |   |  |  + -----
#   |   |  |  | Team
#   |   |  + ------------
#   |   + ------------
#   |   + ------------
#   |   | Category
#   |   |  + --------
#   + ---------------------

    
    
        

# Generate the hidden team rider event table
def rider_event_table(doc, tag, text, team_rider, team_rider_event, team_events):
    # per rider events table - event rows
    #print('rider_event_table %s %s(%s) %s(%s)' % (team_rider, team_rider_event, len(team_rider_event), team_events, len(team_events)))
    with tag('table', width='94%', 
             border=10, klass="dataframe table table-striped table-hover table-sm table-nobordered table-hover"):
        with tag('tbody', klass='tbody'):
            # iterate over the events for the rider
            for eindex, event_result_tuple in list(enumerate(team_rider_event)):
                #print('rider_event_table[%2d] %5s %s' % (eindex, team_rider, event_result))
                event_name, event_result = event_result_tuple
                
                with tag('tr'):
                    #with tag('th', klass='th-event-left', ): text('')
                    #with tag('td', width='70%%', klass='td-event-right', colspan=2, ): text(team_events[eindex])
                    with tag('td', width='70%%', klass='td-event-right', colspan=2, ): text(event_name)
                    with tag('td', width='30%%', klass='td-event-center', ): text(event_result)

# Generate the hidden team rider results table
def team_rider_table(doc, tag, text, category, team, team_rider_results, team_rider_events, team_events):
    # per team riders table - rider rows
    with tag('table', width='50%', 
             border=10, klass="dataframe table table-striped table-hover table-sm table-nobordered table-hover"):
        with tag('tbody', klass='tbody'):
            total = 0
            # iterate over the riders in the team
            for rindex, (rider, rider_total) in enumerate(team_rider_results[category][team].items()):
                team_rider = f"{team.replace(' ', '_')}-{rider.replace(' ', '_')}"
                total += rider_total
                # per rider tr, click to toggle visibility of the inner riders event table
                with tag('tr', 
                    onclick=f"eventToggleVisibilityTimeout('{team_rider}')", klass="event-row"):
                    with tag('td', width='7%%',  klass='td-rider-center', ): text(rindex+1)
                    with tag('td', width='84%%', klass='td-rider-left', ): text(rider)
                    with tag('td', width='7%%',  klass='td-rider-center', ): text('%d' % rider_total)

                # per rider inner event table in a hidden row, shows the events and their points
                with tag('tr', klass='hidden-event-row', data_event=f"{team_rider}"):
                    with tag('td', colspan='3'):
                        rider_event_table(doc, tag, text, team_rider, team_rider_events[category][team][rider], team_events)

            # total row for the rider if more than two results
           #if rindex > 0:
           #    with tag('tr'):
           #        with tag('td', width='84%%',  klass='td-rider-right', colspan=2): text('Total')
           #        with tag('td', width='16%%', klass='td-rider-right', ): text('%d' % total)

# This builds a table for each category:
#   It has a row for each team with the total points:
#       When a team is clicked, it expands to show the riders and their points:
#           When a rider is clicked, it expands to show the events and their points:
#
def category_table(doc, tag, text, category, results, team_rider_results, team_rider_events, team_events):
    # per category teams table
    with tag('table', width='98%', 
             border=1, klass="dataframe table table-striped table-hover table-sm table-nobordered"):
        with tag('tbody', klass='tbody'):
            # iterate over the teams
            for tindex, (team, total) in enumerate(results.items()):
                # per team tr, click to toggle visibility of the inner rider table
                #print('category_table[%2d] %5s %s' % (tindex, total, team))
                category_team = f"{category.replace(' ', '_')}, {team.replace(' ', '_')}"
                with tag('tr', 
                    onclick=f"teamToggleVisibilityTimeout('{category_team}')", klass="team-row"):
                    with tag('td', width='7%%',  klass='td-team-center', ): text(tindex+1 if team != 'Independent' else '')
                    with tag('td', width='84%%', klass='td-team-left', ): text(team)
                    with tag('td', width='7%%',  klass='td-team-center', ): text('%d' % total)

                # the per team inner rider table in a hidden row, shows the riders and their points
                with tag('tr', width='98%', klass='hidden-rider-row', data_team=category_team):
                    with tag('td', colspan='3'):
                        team_rider_table(doc, tag, text, category, team, team_rider_results, team_rider_events, team_events)


def create_html(xlsx_filename, html_filename, date, team_rider_results, team_results, team_rider_events, team_events):
    title = xlsx_filename.replace('.xlsx', '')
    title = title.replace('_', ' ').replace('-', ' ') + ' Team Results'
    #print('filename: %s' % filename)
    #print('title: %s' % title)

    doc, tag, text = Doc().tagtext()
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
        # head, including bootstrap and title, and some custom css
        with tag('head'):
            with tag('link',
                     rel="stylesheet",
                     href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css",
                     integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh",
                     crossorigin="anonymous",
                     ):
                pass
            doc.asis('<meta name="viewport" content="width=device-width, initial-scale=1">')
            doc.asis('<meta http-equiv="cache-control" content="no-cache, no-store, must-revalidate">')
            doc.asis('<meta http-equiv="pragma" content="no-cache">')
            doc.asis('<meta http-equiv="expires" content="0">')
            #with tag('meta'): doc.asis('"viewport" content="width=device-width, initial-scale=1"')

            with tag('title'): text('Team Results')

            # Embed the favicon as a data URI
            with tag('link', rel='icon', type='image/png', href=f"data:image/png;base64,{FAVICON_DATA}"):
                pass

            body_style = """
                    @media only screen and (min-width: 576px)  { body {background-color: lightsalmon; font-size: 140%;}}
                    @media only screen and (min-width: 768px)  { body {background-color: lightgreen;  font-size: 140%;}}
                    @media only screen and (min-width: 992px)  { body {background-color: lightblue;   font-size: 100%;}}
                    @media only screen and (min-width: 1200px) { body {background-color: lightcoral;  font-size: 100%;}}
                    @media only screen and (min-width: 1400px) { body {background-color: lightcyan;   font-size: 100%;}}
                body { 
                    color: black; 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    user-select: text; }
                """
            with tag('style'):
                doc.asis('.table-hover tbody tr:hover { background-color: transparent; }')

                doc.asis(f'thead {{ background: {table_color}; color: white; text-align: left; }}')
                #doc.asis('body { background-color: #FFF; color: black; font-family: Arial, sans-serif; user-select: text; }')
                #doc.asis(body_style)
                doc.asis('tbody { background-color: #FFF; color: black; font-family: Arial, sans-serif; user-select: text; }')
                doc.asis('table { border: 1px solid #FFF; border-collapse: collapse; background-color: #fff; user-select: text }')
                doc.asis('table-noborder { border: 1px solid #fff; border-collapse: collapse; background-color: #fff; border-top: #fff; user-select: text }')
                #doc.asis('th, td { border: 1px solid #cccccc; padding: 8px; text-align: left; }')
                doc.asis('th, td { border: 1px ; background-colour: #FFF; padding: 8px; text-align: left; }')
                doc.asis('.hidden-category-row { display: none; background-colour: #FFF;  }')
                doc.asis('.hidden-rider-row { display: none; background-colour: #FFF; width: 100%; }')
                doc.asis('.hidden-event-row { display: none; background-colour: #FFF;  }')

                doc.asis('.th-outer             { text-align: left; }') 
                doc.asis('.td-outer-left        { text-align: center; }') 
                doc.asis('.td-outer-right       { text-align: right; }') 

                # Categories table - category rows
                doc.asis(f'.th-hidden            {{ background: {table_color};    color: white; text-align: center;  font-size: smaller;}}') 
                doc.asis(f'.th-hidden-right      {{ background: {table_color};    color: white; text-align: right;   font-size: smaller;}}') 
                doc.asis(f'.th-category-center   {{ background: {table_color};    color: white; text-align: center;  font-size: bigger; }}') 
                doc.asis(f'.th-category-left     {{ background: {table_color};    color: black; text-center: left;   font-size: bigger; }}') 
                doc.asis(f'.th-category-right    {{ background: {table_color};    color: black; text-align: right;   font-size: bigger; }}') 

                # per category teams table - team rows
                doc.asis('.td-team-left         { background: white; color: black; text-align: left;    font-weight: bigger; font-weight: bold; overflow: hidden;}') 
                doc.asis('.td-team-right        { background: white; color: black; text-align: right;   font-weight: bigger; font-weight: bold; overflow: hidden;}') 
                doc.asis('.td-team-center       { background: white; color: black; text-align: center;  font-weight: bigger; font-weight: bold; overflow: hidden;}') 

                # per team riders table - rider rows
                doc.asis('.td-rider-center      { background: white; color: black; text-align: center;  font-size: smaller; overflow: hidden; white-space: nowrap;}') 
                doc.asis('.td-rider-left        { background: white; color: black; text-align: left;    font-size: smaller; overflow: hidden; white-space: nowrap;}') 
                doc.asis('.td-rider-right       { background: white; color: black; text-align: right;   font-size: smaller; overflow: hidden; white-space: nowrap;}') 

                # per rider events table - event rows
                doc.asis('.td-event-left        { background: white; color: black; text-align: center;  font-size: smaller; font-weight: bold; overflow: hidden;}') 
                doc.asis('.td-event-right       { background: white; color: black; text-align: right;   font-size: smaller; font-weight: bold; overflow: hidden;}') 
                doc.asis('.td-event-center      { background: white; color: black; text-align: center;  font-size: smaller; font-weight: bold; overflow: hidden;}') 


            #style='min-width:10px;'
            #style='min-width:80px; 
            #style='min-width:10px; 

            with tag('script'):
                doc.asis(toggleVisibility)

        # body, including a container div, title and last updated, and the category tables
        with tag('body'):
            with tag('div', klass='container'):
                with tag('p'): pass

                # title and last updated, currently using a table for the formatting
                # top level Categories table
                with tag('table', width='100%', 
                         border=1, klass='dataframe table table-striped table-hover table-sm table-nobordered table-hover'):
                    with tag('thead'):
                        #with tag('tr'):
                        #    with tag('th', colspan='3'):
                        with tag('tr', style='text-align: left;'):
                            with tag('th', colspan=2): text(title)
                            with tag('th', style='text-align: right;'): text(f'Last Updated: {date}')
                    with tag('tbody', klass='tbody'):
                        # iterate over the categories
                        for cindex, (category, results) in enumerate(team_results.items()):
                            #print('category[%2d] %s' % (cindex, category))
                            toggleButton = f"toggleButton-{category}".replace(' ', '_')
                            toggleDisplay = f"toggleDisplay-{category}".replace(' ', '_')
                            dataCategory = f"data_category-{category}".replace(' ', '_')
                            with tag('tr',
                                     onclick=f"categoryToggleVisibility('{dataCategory}', '{toggleButton}', '{toggleDisplay}', null)", 
                                     klass="category-row"
                                     ):
                                with tag('th', klass='th-category-center', id=toggleButton): text('+')
                                with tag('th', klass='th-category-left', ): text(category)
                                with tag('th', klass='th-category-right', id=toggleDisplay, style='text-align:right'): text('')
                            with tag('tr', klass='hidden-category-row', data_category=f"{dataCategory}"):
                                with tag('td', colspan=4):
                                    category_table(doc, tag, text, category, results, team_rider_results, team_rider_events, team_events[category])
                        #with tag('tr'):
                        #    with tag('th', colspan='3'):
                        toggleButton = 'toggleDesignedBy'
                        with tag('tr', 
                                 onclick=f"categoryToggleVisibility('designedBy', null, null, '{toggleButton}')", 
                                 style='text-align: left;'):
                            with tag('th', klass='th-hidden-right', colspan=3, id=toggleButton): text('Wimsey Timing Services')


    # write it out
    with open(html_filename, 'w') as f:
        f.write(indent(doc.getvalue(), indent_text=False))

TeamResults = {}
TeamRiderResults = {}
TeamRiderEvents = {}
TeamEvents = {}


# Master Men 40+ (Men)
#
# Pos   Name                License     Team         Points Gap Aldergrove Long-1   Southie Circuit-1
#   1   BENNETT, Matthew    BC41342     PVR-ACT Fast    92      55 (1st) +30        37 (1st) +12
#   2   HARRINGTON, Will    TEMP        Meraloma        55  37  32 (3rd) +12        23 (3rd) +3
#   3   TESSIER, nathan     TEMP        Gastown         41  51  24 (4th) +6         17 (6th) +2
#   4   AMANSE, Joseph      PR2307197   PVR-ACT Fast    34  58  16 (5th)            18 (7th) +4

def xlrd_iterate_excel_rows(filename):
    wb = open_workbook(filename)
    for sheet in wb.sheets():
        cat_teams = {}
        cat_rider_results = {}
        cat_rider_events = {}
        event_names = []
        for row_index in range(sheet.nrows):
            row = sheet.row(row_index)
            cellzero = row[0]
            # look for Pos line to get the event names
            if cellzero.ctype == xlrd.XL_CELL_TEXT:
                  if cellzero.value == 'Pos':
                      for col_index in range(6,sheet.ncols):
                          event_names.append(row[col_index].value)
                  continue
            # skip lines that don't start with a number
            if cellzero.ctype != xlrd.XL_CELL_NUMBER:
                continue
            # lines that start with a number are the rider results
            rider = row[1].value
            team = row[3].value
            points = row[4].value
            if team not in cat_teams:
                cat_teams[team] = 0
                cat_rider_results[team] = {}
                cat_rider_events[team] = {}
            if rider not in cat_rider_results[team]:
                cat_rider_results[team][rider] = 0
                cat_rider_events[team][rider] = []

            cat_teams[team] += points
            cat_rider_results[team][rider] += points
            for col_index in range(6,sheet.ncols):
                #print('row[%d][%d][%s:%s] %s' % (row_index, col_index, team, rider, row[col_index].value))
                result = (event_names[col_index-6], row[col_index].value)
                if result == '':
                    continue
                cat_rider_events[team][rider].append(result)

            if len(cat_rider_events[team][rider]) > len(event_names):
                print('WARNING: %s probable TEMP events: %s more than %s' % ( rider, len(cat_rider_events[team][rider]), len(event_names)))


        sorted_results = dict(sorted(cat_teams.items(), key=operator.itemgetter(1), reverse=True))
        #print('sorted_results:', sorted_results.keys())
        if 'Independent' in sorted_results:
            independent = sorted_results['Independent']
            del sorted_results['Independent']
            sorted_results['Independent'] = independent
            #print('sorted_results:', sorted_results.keys())
        TeamResults[sheet.name] = sorted_results
        TeamRiderResults[sheet.name] = cat_rider_results
        TeamRiderEvents[sheet.name] = cat_rider_events
        TeamEvents[sheet.name] = event_names
    return
    print('%20s' % (sheet.name, ))
    for tindex, (team, team_total) in enumerate(TeamResults[sheet.name].items()):
        print('   [%2d] %5s %s' % (tindex, team_total, team))
        for rindex, (rider, rider_total) in enumerate(TeamRiderResults[sheet.name][team].items()):
            print('   [%2d%2d] %5s %s' % (tindex, rindex, rider_total, rider))
            for eindex, event_name in list(enumerate(TeamRiderEvents[sheet.name][team][rider])):
                  print('      [%2d%2d%2d] %5s %s' % (tindex, rindex, eindex, event_name, TeamEvents[sheet.name][eindex]))
    print('-------------------------------------')



def safe_float(value):
    """ Convert value to float safely, returning 0 if conversion fails. """
    try:
        return float(value) if value not in [None, "", " "] else 0.0
    except ValueError:
        return 0.0

def iterate_excel_rows(filename):
    wb = load_workbook(filename, data_only=True)
    for sheet in wb.worksheets:
        cat_teams = {}
        cat_rider_results = {}
        cat_rider_events = {}
        event_names = []
        event_start_index = 7  # events now start at column 7 due to 'Gap' column

        for row_index, row in enumerate(sheet.iter_rows(values_only=True)):
            cellzero = row[0]
            
            # Header row with event names
            if isinstance(cellzero, str) and cellzero.strip().lower() == "pos":
                event_names = list(row[event_start_index:])  # skip 'Gap'
                continue

            # Skip non-numeric starting rows
            if not isinstance(cellzero, (int, float)):
                continue

            rider = row[1] or "Unknown"
            team = row[4] or "Independent"
            points = safe_float(row[5])  # column 5 is Points

            if team not in cat_teams:
                cat_teams[team] = 0
                cat_rider_results[team] = {}
                cat_rider_events[team] = {}

            if rider not in cat_rider_results[team]:
                cat_rider_results[team][rider] = 0
                cat_rider_events[team][rider] = []

            cat_teams[team] += points
            cat_rider_results[team][rider] += points

            # Extract event results starting after 'Gap'
            for col_index, event_name in enumerate(event_names):
                result = row[col_index + event_start_index]
                if result not in [None, ""]:
                    cat_rider_events[team][rider].append((event_name, result))

        # Sort teams and put Independent last
        sorted_results = dict(sorted(cat_teams.items(), key=operator.itemgetter(1), reverse=True))
        if "Independent" in sorted_results:
            independent = sorted_results.pop("Independent")
            sorted_results["Independent"] = independent

        TeamResults[sheet.title] = sorted_results
        TeamRiderResults[sheet.title] = cat_rider_results
        TeamRiderEvents[sheet.title] = cat_rider_events
        TeamEvents[sheet.title] = event_names

FAVICON_DATA = (
    "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"
)
XFAVICON_DATA = (
    "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"
    "ZtAGiJZpDK77ybq"
)



if __name__ == "__main__":
    xlsx_filename = sys.argv[1]
    if len(sys.argv) > 2:
        html_filename = sys.argv[2]
    else:
        html_filename = xlsx_filename.replace('.xlsx', '_Teams.html')
        
    m_time = os.path.getmtime(xlsx_filename)
    dt_m = datetime.datetime.fromtimestamp(m_time).strftime('%Y-%m-%d %H:%M:%S')

    iterate_excel_rows(xlsx_filename)
    create_html(xlsx_filename, html_filename, dt_m, TeamRiderResults, TeamResults, TeamRiderEvents, TeamEvents)

