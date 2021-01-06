#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse


# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

SHOT_SRC = 'del_shots.json'

LEAGUE_WIDE_STATS_TGT = 'del_league_stats.json'


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(description='Calculate league-wide statistics.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of league-wide statistics')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2020,
        type=int, choices=[2016, 2017, 2018, 2019, 2020],
        metavar='season to process data for',
        help="The season information will be processed for")

    args = parser.parse_args()
    initial = args.initial
    season = args.season

    print("+ Retrieving league-wide stats for %d season" % season)

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))

    shot_src_path = os.path.join(tgt_dir, SHOT_SRC)

    shots = json.loads(open(shot_src_path).read())

    # retaining only shots from regular season or playoff games
    shots = list(filter(lambda d: d['season_type'] in ['RS', 'PO'], shots))
    all_shots_on_goal = list(filter(lambda d: d['target_type'] == 'on_goal', shots))
    all_goals = list(filter(lambda d: d['scored'] is True, all_shots_on_goal))
    shots_on_goal_5v5 = list(filter(lambda d: d['plr_situation'] == '5v5', all_shots_on_goal))
    goals_5v5 = list(filter(lambda d: d['plr_situation'] == '5v5', all_goals))

    all_shots_on_goal = len(all_shots_on_goal)
    all_goals = len(all_goals)
    shots_on_goal_5v5 = len(shots_on_goal_5v5)
    goals_5v5 = len(goals_5v5)

    print("\t+ All shots on goal: %d" % all_shots_on_goal)
    print("\t+ 5v5 shots on goal: %d" % shots_on_goal_5v5)
    print("\t+ All goals: %d" % all_goals)
    print("\t+ 5v5 goals: %d" % goals_5v5)

    if all_shots_on_goal:
        save_pctg = round((1 - all_goals / all_shots_on_goal), 10)
    else:
        save_pctg = 0.
    if shots_on_goal_5v5:
        save_pctg_5v5 = round((1 - goals_5v5 / shots_on_goal_5v5), 10)

    print("\t+ Save percentage: %g" % save_pctg)
    print("\t+ 5v5 Save percentage: %g" % save_pctg_5v5)

    league_data = dict()
    league_data['all_shots_on_goal'] = all_shots_on_goal
    league_data['all_goals'] = all_goals
    league_data['shots_on_goal_5v5'] = shots_on_goal_5v5
    league_data['goals_5v5'] = goals_5v5
    league_data['save_pctg'] = save_pctg
    league_data['save_pctg_5v5'] = save_pctg_5v5

    tgt_path = os.path.join(tgt_dir, LEAGUE_WIDE_STATS_TGT)
    # dumping combined game stats for all players
    open(tgt_path, 'w').write(json.dumps(league_data, indent=2))
