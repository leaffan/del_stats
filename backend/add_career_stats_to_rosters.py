#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import json

# loading external configuration
CONFIG = yaml.load(open('config.yml'))

SEASON = 2019
SEASON_TYPE = 1

# TODO: get current season's goalie stats

if __name__ == '__main__':

    teams = CONFIG['teams']

    roster_stats_src_dir = os.path.join(
        CONFIG['base_data_dir'], 'roster_stats', str(SEASON), str(SEASON_TYPE))
    goalie_stats_src_dir = os.path.join(
        CONFIG['tgt_processing_dir'], str(CONFIG['default_season']))
    goalie_stats_src_path = os.path.join(
        goalie_stats_src_dir, 'del_goalie_game_stats_aggregated.json')
    goalie_stats = json.loads(open(goalie_stats_src_path).read())
    career_stats_src_path = os.path.join(
        CONFIG['base_data_dir'], 'career_stats', 'career_stats.json')
    career_stats = json.loads(open(career_stats_src_path).read())

    tgt_dir = os.path.join(
        CONFIG['tgt_processing_dir'], 'career_stats', 'per_team')
    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)

    for fname in os.listdir(roster_stats_src_dir):
        team = teams[int(os.path.splitext(fname)[0])]
        roster_src = os.path.join(roster_stats_src_dir, fname)
        roster = json.loads(open(roster_src).read())
        for plr in roster:
            plr_id = plr['id']
            if plr['position'] == 'GK':
                for goalie_stat in goalie_stats:
                    if goalie_stat['player_id'] == plr_id:
                        plr['statistics']['w'] = goalie_stat['w']
                        plr['statistics']['l'] = goalie_stat['l']
                        plr['statistics']['so'] = goalie_stat['so']
                        plr['statistics']['toi'] = goalie_stat['toi']
                        plr['statistics']['shots_against'] = goalie_stat[
                            'shots_against']
                        plr['statistics']['goals_against'] = goalie_stat[
                            'goals_against']
                        if plr['statistics']['shots_against']:
                            plr['statistics']['save_pctg'] = round(
                                100 - plr['statistics']['goals_against'] /
                                plr['statistics']['shots_against'] * 100., 3)
                            plr['statistics']['gaa'] = round(
                                plr['statistics']['goals_against'] * 3600 /
                                plr['statistics']['toi'], 2)
                        else:
                            plr['statistics']['save_pctg'] = None
                            plr['statistics']['gaa'] = None
                        break
            for plr_career in career_stats:
                if plr_career['player_id'] == plr_id:
                    if 'all' in plr_career['career']:
                        plr['career'] = plr_career['career']['all']
                    continue
        tgt_path = os.path.join(tgt_dir, "%s_stats.json" % team)
        open(tgt_path, 'w').write(json.dumps(roster, indent=2))
