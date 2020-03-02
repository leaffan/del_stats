#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import yaml
import json

from utils import calculate_age

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

ISO_COUNTRY_CODES = {
    'GER': 'de', 'CAN': 'ca', 'SWE': 'se', 'USA': 'us', 'FIN': 'fi',
    'ITA': 'it', 'NOR': 'no', 'FRA': 'fr', 'LVA': 'lv', 'SVK': 'sk',
    'DNK': 'dk', 'RUS': 'ru', 'SVN': 'si', 'HUN': 'hu', 'SLO': 'si',
    'AUT': 'at', 'CRO': 'hr', 'CZE': 'cz'
}


if __name__ == '__main__':

    roster_stats_src_dir = os.path.join(
        CONFIG['base_data_dir'], 'roster_stats')
    tgt_path = os.path.join(
        CONFIG['tgt_processing_dir'], 'del_players.json')

    print(
        "+ Retrieving all players from roster stats " +
        "in %s" % roster_stats_src_dir)

    # trying to load data from already existing target file
    if os.path.isfile(tgt_path):
        all_players_orig = json.loads(open(tgt_path).read())
        all_players = {int(k): v for (k, v) in all_players_orig.items()}
    else:
        all_players = dict()

    SEASON_SEASON_TYPE_TEAM_ID_REGEX = re.compile(
        R"(\d+)\%s(\d)\%s(\d+)\.json" % (os.sep, os.sep))

    for src_dir, dirs, fnames in os.walk(roster_stats_src_dir):
        dirs.sort()
        for fname in fnames:
            src_path = os.path.join(src_dir, fname)
            match = re.search(SEASON_SEASON_TYPE_TEAM_ID_REGEX, src_path)
            if not match:
                continue
            season, season_type_id, team_id = (
                match.group(1), match.group(2), match.group(3))
            season_type = CONFIG['game_types'][int(season_type_id)]
            team = CONFIG['teams'][int(team_id)]
            roster = json.loads(open(src_path).read())
            print(
                "+ Loading %d players from " % len(roster) +
                "%s %s %s roster" % (season, team, season_type))
            for plr in roster:
                single_plr = dict()
                single_plr['player_id'] = int(plr['id'])
                single_plr['first_name'] = plr['firstname']
                single_plr['last_name'] = plr['surname']
                single_plr['position'] = plr['position']
                if 'dateOfBirth' in plr:
                    single_plr['dob'] = plr['dateOfBirth']
                    single_plr['age'] = calculate_age(single_plr['dob'])
                if plr['nationalityShort'] in ISO_COUNTRY_CODES:
                    single_plr['iso_country'] = ISO_COUNTRY_CODES[
                        plr['nationalityShort']]
                else:
                    print(
                        "Nationality abbreviation not " +
                        "recognized: %s" % plr['nationalityShort'])
                    single_plr['iso_country'] = 'n/a'
                all_players[single_plr['player_id']] = single_plr

    all_players = dict(sorted(all_players.items()))

    open(tgt_path, 'w').write(
        json.dumps(all_players, indent=2))
