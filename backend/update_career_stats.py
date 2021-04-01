#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml

from collections import defaultdict

'''
Script to update career stats for all active DEL players using a dataset containing pre-season career stats and current
season's aggregated stats.
'''

CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

SEASON = 2020

SKATER_MAPPING = {
    'games_played': 'gp', 'goals': 'g', 'assists': 'a', 'points': 'pts', 'plus_minus': 'plus_minus',
    'pim_from_events': 'pim', 'pp_goals': 'ppg', 'sh_goals': 'shg', 'gw_goals': 'gwg', 'shots_on_goal': 'sog',
    'shot_pctg': 'sh_pctg', 'goals_per_game': 'gpg', 'assists_per_game': 'apg', 'points_per_game': 'ptspg',
}
GOALIE_MAPPING = {
    'games_played': 'gp', 'time_on_ice': 'min', 'w': 'w', 'l': 'l', 'so': 'so', 'goals_against': 'ga', 'toi': 'toi',
    'shots_against': 'sa',  'save_pctg': 'sv_pctg', 'gaa': 'gaa',
}

if __name__ == '__main__':

    pre_career_stats_src_path = os.path.join(CONFIG['base_data_dir'], 'career_stats', 'pre_season_career_stats.json')
    goalie_season_stats_src_path = os.path.join(
        CONFIG['tgt_processing_dir'], str(SEASON), 'del_goalie_game_stats_aggregated.json')
    skater_season_stats_src_path = os.path.join(
        CONFIG['tgt_processing_dir'], str(SEASON), 'del_player_game_stats_aggregated.json')

    # creating target directory for per player career stats data (if necessary)
    per_player_career_stats_tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], 'career_stats', 'per_player')
    if not os.path.isdir(per_player_career_stats_tgt_dir):
        os.makedirs(per_player_career_stats_tgt_dir)

    # loading pre-season career stats
    pre_career_data = json.loads(open(pre_career_stats_src_path).read())
    # loading aggregated season stats
    goalie_season_stats = json.loads(open(goalie_season_stats_src_path).read())
    skater_season_stats = json.loads(open(skater_season_stats_src_path).read())[-1]

    upd_career_data = list()

    for career in pre_career_data[:]:
        plr_id = career['player_id']

        print("+ Updating career data for %s %s (%s) [%d]" % (
            career['first_name'], career['last_name'], career['position'], career['player_id']))

        upd_career = career

        # retrieving current player's season stats, depending on position
        if career['position'] != 'GK':
            season_stats = list(filter(lambda d: d['player_id'] == plr_id, skater_season_stats))
        else:
            season_stats = list(filter(lambda d: d['player_id'] == plr_id, goalie_season_stats))

        for ssl in season_stats:
            season_type = ssl['season_type']
            # skipping all non-regular-season or non-playoff games
            if season_type not in ['RS', 'PO']:
                continue
            # setting up stat line for current season and season type, i.e. phase
            new_career_stats_line = dict()
            new_career_stats_line['season'] = SEASON
            new_career_stats_line['season_type'] = season_type
            new_career_stats_line['team'] = ssl['team']
            if season_type not in career['career']:
                career['career'][season_type] = defaultdict(int)
            if 'all' not in career['career']:
                career['career']['all'] = defaultdict(int)
            # adding current season's stats to pre-season career stats...
            if career['position'] != 'GK':
                # ...for skaters
                for param in SKATER_MAPPING:
                    new_career_stats_line[SKATER_MAPPING[param]] = ssl[param]
                    try:
                        career['career'][season_type][SKATER_MAPPING[param]] += ssl[param]
                        career['career']['all'][SKATER_MAPPING[param]] += ssl[param]
                    except Exception:
                        print("+ Unable to retrieve '%s' from season stat line" % param)
            else:
                # ...for goaltenders
                for param in GOALIE_MAPPING:
                    new_career_stats_line[GOALIE_MAPPING[param]] = ssl[param]
                    if param == 'w':
                        new_career_stats_line['t'] = 0
                    if param == 'goals_against':
                        new_career_stats_line['sv'] = ssl['shots_against'] - ssl['goals_against']
                    if param == 'time_on_ice':
                        new_career_stats_line['min'] = "%d:%02d" % (ssl['toi'] // 60, ssl['toi'] % 60)
                        continue
                    try:
                        career['career'][season_type][GOALIE_MAPPING[param]] += ssl[param]
                        career['career']['all'][GOALIE_MAPPING[param]] += ssl[param]
                    except Exception:
                        print("+ Unable to retrieve '%s' from season stat line" % param)
            # updating current player's full career stats
            upd_career['seasons'].append(new_career_stats_line)

        plr_career = upd_career['career']
        # finally re-calculating percentages and rates for each season type group ('RS', 'PO', 'all')
        for key in list(plr_career.keys()):
            # either for skaters...
            if upd_career['position'] != 'GK':
                if not plr_career[key]['gp']:
                    del plr_career[key]
                    continue
                if plr_career[key]['sog']:
                    plr_career[key]['sh_pctg'] = round(plr_career[key]['g'] / plr_career[key]['sog'] * 100, 2)
                else:
                    plr_career[key]['sh_pctg'] = None
                if plr_career[key]['gp']:
                    plr_career[key]['gpg'] = round(plr_career[key]['g'] / plr_career[key]['gp'], 2)
                    plr_career[key]['apg'] = round(plr_career[key]['a'] / plr_career[key]['gp'], 2)
                    plr_career[key]['ptspg'] = round(plr_career[key]['pts'] / plr_career[key]['gp'], 2)
                else:
                    plr_career[key]['gpg'] = None
                    plr_career[key]['apg'] = None
                    plr_career[key]['ptspg'] = None
            # ...or for goalies
            else:
                if not plr_career[key]['toi']:
                    del plr_career[key]
                    continue
                plr_career[key]['sv'] = plr_career[key]['sa'] - plr_career[key]['ga']
                if plr_career[key]['sa']:
                    plr_career[key]['sv_pctg'] = round(100 - plr_career[key]['ga'] / plr_career[key]['sa'] * 100., 3)
                else:
                    plr_career[key]['sv_pctg'] = None
                if plr_career[key]['toi']:
                    plr_career[key]['gaa'] = round(plr_career[key]['ga'] * 3600 / plr_career[key]['toi'], 2)
                    plr_career[key]['min'] = "%d:%02d" % (plr_career[key]['toi'] // 60, plr_career[key]['toi'] % 60)
                else:
                    plr_career[key]['gaa'] = None
                    plr_career[key]['min'] = "%d:%02d" % (0, 0)

        upd_career_data.append(upd_career)

        # saving updated career stats per player
        per_player_career_stats_tgt_path = os.path.join(per_player_career_stats_tgt_dir, "%d.json" % plr_id)
        if upd_career:
            open(per_player_career_stats_tgt_path, 'w').write(json.dumps(upd_career, indent=2))

    # saving updated career stats for all players
    upd_career_stats_tgt_path = os.path.join(CONFIG['tgt_processing_dir'], 'career_stats', 'updated_career_stats.json')

    if upd_career_data:
        open(upd_career_stats_tgt_path, 'w').write(json.dumps(upd_career_data, indent=2))
