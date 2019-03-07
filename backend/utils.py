#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import date

name_corrections = {
    # Coaches
    'Dahlem Fabian': 'Fabian Dahlem',
    'Draisaitl Peter': 'Peter Draisaitl',
    'Popiesch Thomas': 'Thomas Popiesch',
    'Herold Kreis': 'Harold Kreis',
    'Gross Pavel': 'Pavel Gross',
    'MIke Stewart': 'Mike Stewart',
    'Michael Stewart': 'Mike Stewart',
    'Jodoi Clement': 'Clément Jodoin',
    'Jodoin Clement': 'Clément Jodoin',
    'Clement Jodoin': 'Clément Jodoin',
    'Jamie Bartmann': 'Jamie Bartman',
    # Arenas
    'Curt Frenzel Stadium': 'Curt-Frenzel-Stadion',
    'Arena NBG Versicheru': 'Arena Nürnberger Versicherung'
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
    Gets abbreviation for team aassociated with specified
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
