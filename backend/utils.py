#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import math
from datetime import date, timedelta

from dateutil.parser import parse

coaches = [
    'Tray Tuomie', 'Serge Aubin', 'Thomas Popiesch', 'Harold Kreis',
    'Doug Shedden', "Jason O'Leary", 'Mike Stewart', 'Brandon Reid',
    'Pavel Gross', 'Don Jackson', 'Kurt Kleinendorst', 'Paul Thompson',
    'Tom Pokel', 'Pat Cortina', 'Peter Draisaitl', 'Clément Jodoin',
    'Jamie Bartman', 'Stephane Richer', 'Matthias Roos', 'Tommy Samuelsson',
    'Uwe Krupp', 'Bill Stewart', 'Mike Pellegrims', 'Rob Leask',
    'Rick Adduono', 'Sean Simpson', 'Rob Wilson', 'Cory Clouston', 'Rob Daum',
    'Marian Bazany', 'Jari Pasanen', 'Fabian Dahlem', 'Tobias Abstreiter',
    'Larry Mitchell', 'Kevin Gaudet', 'Pekka Tirkkonen', 'Martin Jiranek',
    'Hans Kossmann', 'Dan Lacroix', 'Jürgen Rumrich', 'Franz-David Fritzmeier',
    'Christoph Kreutzer', 'Manuel Kofler', 'Pierre Beaulieu', 'Steve Walker',
    'Niklas Sundblad', 'Glen Hanlon',
]


name_corrections = {
    # coaches
    'Thomas Popisch': 'Thomas Popiesch',
    'Tom Pokle': 'Tom Pokel',
    'Paul Thompsen': 'Paul Thompson',
    'Kurt Kleindorst': 'Kurt Kleinendorst',
    'Manuell Kofler': 'Kurt Kleinendorst',
    'Tray Toumie': 'Tray Tuomie',
    'Herold Kreis': 'Harold Kreis',
    'MIke Stewart': 'Mike Stewart',
    'Mike Steward': 'Mike Stewart',
    'Jodoi Clement': 'Clément Jodoin',
    'Michael Stewart': 'Mike Stewart',
    'Bill Steward': 'Bill Stewart',
    'Rick Adduno': 'Rick Adduono',
    'Rob Willson': 'Rob Wilson',
    'Pet Cortina': 'Pat Cortina',
    'Jason O Leary': "Jason O'Leary",
    'Jason O´Leary': "Jason O'Leary",
    'Cortina': 'Pat Cortina',
    'Stewart': 'Mike Stewart',
    'Larry Mitchel': 'Larry Mitchell',
    'Dahlem Fabian': 'Fabian Dahlem',
    'Draisaitl Peter': 'Peter Draisaitl',
    'Popiesch Thomas': 'Thomas Popiesch',
    'Gross Pavel': 'Pavel Gross',
    'Jodoin Clement': 'Clément Jodoin',
    'Clement Jodoin': 'Clément Jodoin',
    'Jamie Bartmann': 'Jamie Bartman',
    'Richer Stephane': 'Stephane Richer',
    'Stewart Mike': 'Mike Stewart',
    'Roos Matthias': 'Matthias Roos',
    'Jason O`Leary': "Jason O'Leary",
    'J. O`Leary': "Jason O'Leary",
    'Pellegrims Mike': 'Mike Pellegrims',
    'Krupp Uwe': 'Uwe Krupp',
    'Jackson Don': 'Don Jackson',
    'Simpson Sean': 'Sean Simpson',
    'Robert Daum': 'Rob Daum',
    'Pokel Tom': 'Tom Pokel',
    'Daum Rob': 'Rob Daum',
    'Shedden Doug': 'Doug Shedden',
    'Mark Draisaitl': 'Peter Draisaitl',
    'Kreutzer Christoph': 'Christoph Kreutzer',
    'Pasanen Jari': 'Jari Pasanen',
    'Franz Fritzmeier': 'Franz-David Fritzmeier',
    'Fritzmeier': 'Franz-David Fritzmeier',
    # at times former assistants become head coaches and
    # therefore their names no longer need to be adjusted
    # hence: the following name corrections are only valid until the date
    # specified after the pipe symbol
    'Pienne Beaulieu': 'Pierre Beaulieu',
    'Pierre Beaulie': 'Pierre Beaulieu',
    'Pierre Beaulien': 'Pierre Beaulieu',
    'Pierre Beaulieu': 'Brandon Reid|2019-12-12',
    # following are individual corrections valid only for the accompanying
    # game date
    'Don Jackson': 'Steve Walker//2020-01-19',
    # following are individual corrections valid only for the specified
    # combination of game id and team abbreviation as a workaround for
    # entirely missing coach information
    '1315_KEC': 'Peter Draisaitl',
    '1315_DEG': 'Harold Kreis',
    '1375_MAN': 'Pavel Gross',
    '1738_IEC': "Jason O'Leary",
    '1738_KEV': 'Pierre Beaulieu',
    '1691_STR': 'Tom Pokel',
    '1691_WOB': 'Pat Cortina',
    '1794_RBM': 'Don Jackson',
    # Arenas
    'Curt Frenzel Stadium': 'Curt-Frenzel-Stadion',
    'Arena NBG Versicheru': 'Arena Nürnberger Versicherung',
}

# defining player name corrections
player_name_corrections = {
    1410: {
        'first_name': 'Patrick Joseph',
        'full_name': 'Patrick Joseph Alber'
    }
}

capacities = {
    'Arena Nürnberger Versicherung': 7672,
    'Curt-Frenzel-Stadion': 6139,
    'Mercedes-Benz Arena': 14200,
    'SAP-Arena': 13600,
    'Eisarena Bremerhaven': 4647,
    'ISS Dome': 13205,
    'Saturn Arena': 4816,
    'Eissporthalle Iserlohn': 4967,
    'Lanxess Arena': 18700,
    'RheinEnergieSTADION': 50000,
    'König Palast': 8029,
    'Yayla-Arena': 8029,
    'Olympia Eishalle': 6142,
    'Helios Arena': 6214,
    'Eisstadion Straubing': 5825,
    'EisArena Wolfsburg': 4503,
}


def get_game_info(game):
    """
    Gets printable game information.
    """
    return (
        "%d (%s: %s [%d] vs. %s [%d])" % (
            game['game_id'], game['date'],
            game['home_team'], game['home_score'],
            game['road_team'], game['road_score'],
        ))


def get_team_from_game(game, home_road):
    """
    Gets abbreviation for team associated with specified
    home/road denominator.
    """
    if home_road == 'home':
        return game['home_abbr']
    elif home_road == 'road':
        return game['road_abbr']
    else:
        return None


def get_season(date_of_interest=None):
    """
    Identifies season based on month of given date, anything until June
    belongs to the season ending in the date's year, anything after
    June belongs to the season beginning in the date's year.
    """
    if date_of_interest is None:
        date_of_interest = date.today()
    if date_of_interest.month < 7:
        season = date_of_interest.year - 1
    else:
        season = date_of_interest.year

    return season


def get_game_type_from_season_type(game):
    """
    Determines game type (as used in storage directories) from season type
    (e.g RS or PO) as stored in game definition.
    """
    if game['season_type'] == 'RS':
        return 1
    elif game['season_type'] == 'PO':
        return 3
    elif game['season_type'] == 'MSC':
        return 4
    else:
        return 0


def get_home_road(game, event):
    """
    Determines whether specified game and event combination is related to the
    home or the road team.
    """
    if event['data']['team'] == 'home':
        return game['home_abbr'], 'home'
    else:
        return game['road_abbr'], 'road'


def calculate_age(dob):
    """
    Calculates current age of player with specified date of birth.
    """
    # parsing player's date of birth
    dob = parse(dob).date()
    # retrieving today's date
    today = date.today()
    # projecting player's date of birth to this year
    # checking if player was born in a leap year first
    if (
        dob.month == 2 and dob.day == 29
    ):
        # moving player's date of birth forward then
        dob = dob + timedelta(days=1)
    this_year_dob = date(today.year, dob.month, dob.day)

    # if this year's birthday has already passed...
    if (today - this_year_dob).days >= 0:
        # calculating age as years since year of birth and days since this
        # year's birthday
        years = today.year - dob.year
        days = (today - this_year_dob).days
    # otherwise...
    else:
        # projecting player's data of birth to last year
        last_year_dob = date(today.year - 1, dob.month, dob.day)
        # calculating age as years between last year and year of birth and days
        # since last year's birthday
        years = last_year_dob.year - dob.year
        days = (today - last_year_dob).days

    # converting result to pseudo-float
    return float("%d.%03d" % (years, days))


def calculate_games_left_till_next_hundred(games):
    if games:
        next_hundred = int(math.ceil(games / 100.0)) * 100
        if games % 100 == 0:
            next_hundred += 100
        games_left = next_hundred - games
    else:
        games_left = 100
    return games_left


def read_del_team_names(src=R"data\del_team_names.csv"):

    # retrieving currently on-going season from current date
    current_season = get_season(date.today())
    # establishing dictionary for team name/abbreviation lookup
    team_lookup = dict()

    with open(src) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            valid_from = int(row['valid_from'])
            team_id = int(row['archive_team_id'])
            if not row['valid_to']:
                valid_to = current_season
            else:
                valid_to = int(row['valid_to'])
            # populating lookup for current team
            for season in range(valid_from, valid_to + 1):
                team_lookup[(team_id, season)] = (
                    row['team_abbr'], row['team_name'])

    return team_lookup


def correct_player_name(single_plr):
    """
    Corrects name items in specified player data set.
    """
    plr_id = single_plr['player_id']
    # retrieving all available correction items for current player
    corrections = player_name_corrections[plr_id]
    # correcting name items, if applicable
    for key in ['first_name', 'last_name', 'full_name']:
        if key in single_plr and key in corrections:
            single_plr[key] = corrections[key]
