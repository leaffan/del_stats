#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import yaml
import json

from datetime import datetime
from collections import defaultdict

from dateutil.parser import parse

from utils import calculate_age, player_name_corrections, correct_player_name, iso_country_codes, get_season

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

U23_CUTOFF_DATES = {
    # a player needs to be born after the specified date to be
    # considered a U23 player during the designated season
    2016: parse("1993-12-31"),
    2017: parse("1994-12-31"),
    2018: parse("1995-12-31"),
    2019: parse("1996-12-31"),
    2020: parse("1997-12-31"),
}

U20_CUTOFF_DATES = {
    # a player needs to be born after the specified date to be
    # eligible for the World Junions during the designated season
    2016: parse("1996-12-31"),
    2017: parse("1997-12-31"),
    2018: parse("1998-12-31"),
    2019: parse("1999-12-31"),
    2020: parse("2000-12-31"),
}

PLAYER_CAREER_SRC_DIR = os.path.join(CONFIG['base_data_dir'], 'career_stats', 'per_player')

# mapping from original attributes to target attributes
PERSONAL_ATTR_MAPPING = {
    'id': 'player_id', 'firstname': 'first_name', 'surname': 'last_name', 'name': 'full_name', 'position': 'position',
    'dateOfBirth': 'dob', 'stick': 'hand', 'height': 'height', 'weight': 'weight',
    'nationalityShort': 'country',
}

# retrieving season at current date
CURRENT_SEASON = get_season()

ALL_PLAYERS_TGT = 'del_players.json'
PER_SEASON_PERSONAL_DATA_TGT = 'del_player_personal_data.json'


def is_rookie(player_data_item, season_of_interest):
    """
    Determines whether specified player was a rookie during provided season of interest.
    """
    # rookies also have to be U23 players
    if not player_data_item['u23']:
        return False

    print("\t+ Checking rookie status of %s" % player_data_item['full_name'])

    # retrieving available career stats for current player
    plr_career_src_path = os.path.join(PLAYER_CAREER_SRC_DIR, "%d.json" % player_data_item['player_id'])
    if not os.path.isfile(plr_career_src_path):
        print("\t+ Career stats for %s [%d] not available from %s" % (
            player_data_item['full_name'], player_data_item['player_id'], plr_career_src_path))
        return False
    # loading player career
    plr_career = json.loads(open(plr_career_src_path).read())

    # players without any career data at all are rookies
    if not plr_career['seasons']:
        return True

    # counting games played per previous season
    games_per_season = defaultdict(int)
    for season in plr_career['seasons']:
        if season['season'] >= season_of_interest:
            continue
        # rookies have played less than 20 games in any previous season
        # therefore players with more games are no rookies anymore
        if season['gp'] >= 20:
            return False
        games_per_season[season['season']] += season['gp']
        # games to be considered also include playoff games
        if games_per_season[season['season']] >= 20:
            return False
    else:
        # remaining players without any previous season with 20 games or more are rookies
        return True


def collect_personal_data(raw_plr, season):
    """
    Collects personal player data from specified raw player data item and the specified season.
    """
    # collecting player's personal data
    personal_data = dict()
    for attr in PERSONAL_ATTR_MAPPING:
        personal_data[PERSONAL_ATTR_MAPPING[attr]] = raw_plr.get(attr, None)

    # setting ISO country code
    if personal_data['country'] in iso_country_codes:
        personal_data['iso_country'] = iso_country_codes[personal_data['country']]
    else:
        print("Nationality abbreviation not recognized: %s" % personal_data['country'])
        personal_data['iso_country'] = 'n/a'

    # optionally correcting player's name
    if int(raw_plr['id']) in player_name_corrections:
        correct_player_name(personal_data)

    # calculating player's age
    if season == CURRENT_SEASON:
        personal_data['age'] = calculate_age(personal_data['dob'])
    else:
        personal_data['age'] = calculate_age(personal_data['dob'], "%d-12-31" % season)

    # identifying u23 status
    if (
        personal_data['dob'] and  # very seldomly no dates of birth are provided
        personal_data['country'] == 'GER' and
        parse(personal_data['dob']) > U23_CUTOFF_DATES[season]
    ):
        personal_data['u23'] = True
    else:
        personal_data['u23'] = False
    # identifying u20 status
    if (
        personal_data['dob'] and  # very seldomly no dates of birth are provided
        parse(personal_data['dob']) > U20_CUTOFF_DATES[season]
    ):
        personal_data['u20'] = True
    else:
        personal_data['u20'] = False
    # identifying rookie status
    personal_data['rookie'] = is_rookie(personal_data, season)

    return personal_data


if __name__ == '__main__':

    roster_stats_src_dir = os.path.join(CONFIG['base_data_dir'], 'roster_stats')
    tgt_path = os.path.join(CONFIG['tgt_processing_dir'], ALL_PLAYERS_TGT)

    print("+ Retrieving all players from roster stats in %s" % roster_stats_src_dir)

    # trying to load data from already existing target file
    if os.path.isfile(tgt_path):
        all_players_orig = json.loads(open(tgt_path).read())
        all_players = {int(k): v for (k, v) in all_players_orig.items()}
    else:
        all_players = dict()

    SEASON_SEASON_TYPE_TEAM_ID_REGEX = re.compile(R"(\d+)\%s(\d)\%s(\d+)\.json" % (os.sep, os.sep))

    # establishing containers to collect player data per season
    per_season_personal_player_data = defaultdict(list)
    # setting up container to register processed player ids per season
    per_season_processed_player_ids = defaultdict(list)

    for src_dir, dirs, fnames in os.walk(roster_stats_src_dir):
        dirs.sort()
        for fname in fnames:
            src_path = os.path.join(src_dir, fname)
            match = re.search(SEASON_SEASON_TYPE_TEAM_ID_REGEX, src_path)
            if not match:
                continue
            # retrieving season, season type id and team id from file name
            season, season_type_id, team_id = (int(match.group(1)), match.group(2), match.group(3))

            season_type = CONFIG['game_types'][int(season_type_id)]

            # not processing player rosters from pre-season tournaments
            if season_type == 'MSC':
                continue

            team = CONFIG['teams'][int(team_id)]
            # loading roster
            roster = json.loads(open(src_path).read())
            print("+ Loading players from %s %s %s roster" % (season, team, season_type))
            for raw_plr in roster:
                player_id = int(raw_plr['id'])
                # checking if player has already been processed for this season
                if player_id in per_season_processed_player_ids[season]:
                    continue

                # collecting player's personal data for season under investigation
                personal_data = collect_personal_data(raw_plr, season)
                per_season_personal_player_data[season].append(personal_data)

                # collecting basic data for full player registry
                single_plr = dict()
                # retaining a few attributes from personal data item
                for attr in ['player_id', 'first_name', 'last_name', 'position', 'hand', 'iso_country', 'dob']:
                    single_plr[attr] = personal_data[attr]
                # full player registry always contains the current age
                single_plr['age'] = calculate_age(single_plr['dob'])

                all_players[single_plr['player_id']] = single_plr

                # adding current player id to list of processed player ids for current season
                # necessary since at times duplicate rosters are provided in original data
                # and to avoid registering players for different season types twice
                per_season_processed_player_ids[season].append(player_id)

    # saving personal data per season
    current_datetime = datetime.now().timestamp() * 1000
    for season in per_season_personal_player_data:
        print(season, len(per_season_personal_player_data[season]))
        pd_tgt_path = os.path.join(CONFIG['tgt_processing_dir'], str(season), PER_SEASON_PERSONAL_DATA_TGT)
        # adding current timestamp to output data
        output_data = [current_datetime, per_season_personal_player_data[season]]
        open(pd_tgt_path, 'w').write(json.dumps(output_data, indent=2))

    # sorting and saving registry of all players
    all_players = dict(sorted(all_players.items()))
    open(tgt_path, 'w').write(json.dumps(all_players, indent=2))
