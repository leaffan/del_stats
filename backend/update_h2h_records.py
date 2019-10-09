#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml

from collections import defaultdict

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

PRE_SEASON_HEAD2HEAD_SRC = 'pre_season_h2h.json'
SEASON_HEAD2HEAD_TGT = 'h2h.json'
TEAM_GAME_SRC = 'del_team_game_stats.json'
SEASON = 2019

if __name__ == '__main__':

    print("+ Updating head-to-head records")

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(SEASON))
    team_games_src_path = os.path.join(tgt_dir, TEAM_GAME_SRC)
    pre_season_h2h_src_path = os.path.join(tgt_dir, PRE_SEASON_HEAD2HEAD_SRC)
    team_games = json.loads(open(team_games_src_path).read())
    h2h_all_time = json.loads(open(pre_season_h2h_src_path).read())

    h2h_records = defaultdict(dict)

    # collecting head-to-head records for current season
    for team_game in team_games[-1]:
        team = team_game['team']
        opp_team = team_game['opp_team']
        h2h_records[team][opp_team] = defaultdict(int)
        h2h_records[team][opp_team]['gp'] += team_game['games_played']
        h2h_records[team][opp_team]['w'] += team_game['w']
        h2h_records[team][opp_team]['l'] += team_game['l']
        home_road = team_game['home_road']
        h2h_records[team][opp_team]["gp_%s" % home_road] += team_game[
            'games_played']
        h2h_records[team][opp_team]["w_%s" % home_road] += team_game['w']
        h2h_records[team][opp_team]["l_%s" % home_road] += team_game['l']

    for team in h2h_all_time:
        for opp_team in h2h_all_time[team]:
            if opp_team in h2h_records[team]:
                for key in [
                    'gp', 'w', 'l',
                    'gp_home', 'w_home', 'l_home',
                    'gp_road', 'w_road', 'l_road'
                ]:
                    h2h_all_time[team][opp_team][key] += (
                        h2h_records[team][opp_team][key])
                    h2h_all_time[team][opp_team]['win_pctg'] = round(
                        h2h_all_time[team][opp_team]['w'] /
                        h2h_all_time[team][opp_team]['gp'] * 100, 2)
                    h2h_all_time[team][opp_team]['win_pctg_home'] = round(
                        h2h_all_time[team][opp_team]['w_home'] /
                        h2h_all_time[team][opp_team]['gp_home'] * 100, 2)
                    h2h_all_time[team][opp_team]['win_pctg_road'] = round(
                        h2h_all_time[team][opp_team]['w_road'] /
                        h2h_all_time[team][opp_team]['gp_road'] * 100, 2)

    tgt_h2h_path = os.path.join(tgt_dir, SEASON_HEAD2HEAD_TGT)
    open(tgt_h2h_path, 'w').write(json.dumps(h2h_all_time, indent=2))
