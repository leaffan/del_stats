#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    return (
        "%d (%s: %s [%d] vs. %s [%d])" % (
            game['game_id'], game['date'],
            game['home_team'], game['home_score'],
            game['road_team'], game['road_score'],
        ))