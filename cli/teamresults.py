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


def create_html(xls_filename, date, team_rider_results, team_results, team_rider_events, team_events):
    filename = xls_filename.replace('.xlsx', '_Teams.html')
    title = xls_filename.replace('.xlsx', '')
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
    with open(filename, 'w') as f:
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
        
        for row_index, row in enumerate(sheet.iter_rows(values_only=True)):
            cellzero = row[0]
            # Look for "Pos" line to get the event names
            if isinstance(cellzero, str) and cellzero.strip() == "Pos":
                event_names = list(row[6:])  # Store event names
                continue
            
            # Skip lines that don't start with a number
            if not isinstance(cellzero, (int, float)):
                continue
            
            # Extract rider data
            rider = row[1] or "Unknown"
            team = row[4] or "Independent"
            points = safe_float(row[5])  # Ensure points is a float
            
            if team not in cat_teams:
                cat_teams[team] = 0
                cat_rider_results[team] = {}
                cat_rider_events[team] = {}
            
            if rider not in cat_rider_results[team]:
                cat_rider_results[team][rider] = 0
                cat_rider_events[team][rider] = []

            # Accumulate team and rider points
            cat_teams[team] += points
            cat_rider_results[team][rider] += points
            
            # Process event results
            for col_index, event_name in enumerate(event_names):
                result = row[col_index + 6]
                if result not in [None, ""]:
                    cat_rider_events[team][rider].append((event_name, result))

        # Sort teams by total points in descending order
        sorted_results = dict(sorted(cat_teams.items(), key=operator.itemgetter(1), reverse=True))
        
        # Ensure "Independent" is always last
        if "Independent" in sorted_results:
            independent = sorted_results.pop("Independent")
            sorted_results["Independent"] = independent

        TeamResults[sheet.title] = sorted_results
        TeamRiderResults[sheet.title] = cat_rider_results
        TeamRiderEvents[sheet.title] = cat_rider_events
        TeamEvents[sheet.title] = event_names



if __name__ == "__main__":
    xls_filename = sys.argv[1]
    m_time = os.path.getmtime(xls_filename)
    dt_m = datetime.datetime.fromtimestamp(m_time).strftime('%Y-%m-%d %H:%M:%S')

    iterate_excel_rows(xls_filename)
    create_html(xls_filename, dt_m, TeamRiderResults, TeamResults, TeamRiderEvents, TeamEvents)

