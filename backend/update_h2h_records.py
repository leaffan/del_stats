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
        games_played = team_game['games_played']
        # setting up new record item for current season if necessary
        if opp_team not in h2h_records[team]:
            h2h_records[team][opp_team] = defaultdict(int)
        curr_record = h2h_records[team][opp_team]
        curr_record['games_played'] += games_played
        curr_record['wins'] += team_game['w']
        curr_record['losses'] += team_game['l']
        curr_record['goals_for'] += team_game['score']
        curr_record['goals_against'] += team_game['opp_score']
        if team_game['game_type'] == 'OT':
            curr_record['ot_games_played'] += games_played
        if team_game['game_type'] == 'SO':
            curr_record['so_games_played'] += games_played
            curr_record['so_wins'] += team_game['w']
            curr_record['so_losses'] += team_game['l']
            curr_record['ot_ties'] += 1
        elif team_game['game_type'] == 'OT':
            curr_record['ot_wins'] += team_game['w']
            curr_record['ot_losses'] += team_game['l']
        if team_game['season_type'] == 'PO':
            curr_record['po_games_played'] += games_played
            curr_record['po_wins'] += team_game['w']
            curr_record['po_losses'] += team_game['l']
            curr_record['goals_for_po'] += team_game['score']
            curr_record['goals_against_po'] += team_game['opp_score']
        if team_game['game_type'] == 'OT' and team_game['season_type'] == 'PO':
            curr_record['po_ot_games_played'] += games_played
            curr_record['po_ot_wins'] += team_game['w']
            curr_record['po_ot_losses'] += team_game['l']
        home_road = team_game['home_road']
        curr_record["%s_games_played" % home_road] += games_played
        curr_record["%s_wins" % home_road] += team_game['w']
        curr_record["%s_losses" % home_road] += team_game['l']
        curr_record['%s_goals_for' % home_road] += team_game['score']
        curr_record['%s_goals_against' % home_road] += team_game['opp_score']
        if team_game['game_type'] == 'OT':
            curr_record["%s_ot_games_played" % home_road] += games_played
            curr_record["%s_ot_wins" % home_road] += team_game['w']
            curr_record["%s_ot_losses" % home_road] += team_game['l']
        if team_game['game_type'] == 'SO':
            curr_record["%s_so_games_played" % home_road] += games_played
            curr_record["%s_so_wins" % home_road] += team_game['w']
            curr_record["%s_so_losses" % home_road] += team_game['l']
        if team_game['season_type'] == 'PO':
            curr_record["%s_po_games_played" % home_road] += games_played
            curr_record["%s_po_wins" % home_road] += team_game['w']
            curr_record["%s_po_losses" % home_road] += team_game['l']
            curr_record['%s_goals_for_po' % home_road] += team_game['score']
            curr_record['%s_goals_against_po' % home_road] += team_game['opp_score']
        if team_game['game_type'] == 'OT' and team_game['season_type'] == 'PO':
            curr_record["%s_po_ot_games_played" % home_road] += games_played
            curr_record["%s_po_ot_wins" % home_road] += team_game['w']
            curr_record["%s_po_ot_losses" % home_road] += team_game['l']

    final_keys = [
        # general parameters
        'games_played', 'wins', 'losses', 'goals_for', 'goals_against',
        # overtime parameters
        'ot_games_played', 'ot_wins', 'ot_losses', 'ot_ties',
        # shootout parameters
        'so_games_played', 'so_wins', 'so_losses',
        # general playoff parameters
        'po_games_played', 'po_wins', 'po_losses', 'goals_for_po', 'goals_against_po',
        # playoff overtime parameters
        'po_ot_games_played', 'po_ot_wins', 'po_ot_losses',
        # general home parameters
        'home_games_played', 'home_wins', 'home_losses', 'home_goals_for', 'home_goals_against',
        # home overtime parameters
        'home_ot_games_played', 'home_ot_wins', 'home_ot_losses', 'home_ot_ties',
        # home shootout parameters
        'home_so_games_played', 'home_so_wins', 'home_so_losses',
        # general home playoff parameters
        'home_po_games_played', 'home_po_wins', 'home_po_losses', 'home_goals_for_po', 'home_goals_against_po',
        # home playoff overtime parameters
        'home_po_ot_games_played', 'home_po_ot_wins', 'home_po_ot_losses',
        # general road parameters
        'road_games_played', 'road_wins', 'road_losses', 'road_goals_for', 'road_goals_against',
        # road overtime parameters
        'road_ot_games_played', 'road_ot_wins', 'road_ot_losses', 'road_ot_ties',
        # road shootout parameters
        'road_so_games_played', 'road_so_wins', 'road_so_losses',
        # general road playoff parameters
        'road_po_games_played', 'road_po_wins', 'road_po_losses', 'road_goals_for_po', 'road_goals_against_po',
        # road playoff overtime parameters
        'road_po_ot_games_played', 'road_po_ot_wins', 'road_po_ot_losses',
    ]

    for team in h2h_all_time:
        for opp_team in h2h_all_time[team]:
            if opp_team in h2h_records[team]:
                for key in final_keys:
                    h2h_all_time[team][opp_team][key] += h2h_records[team][opp_team][key]
                if h2h_all_time[team][opp_team]['games_played']:
                    h2h_all_time[team][opp_team]['win_pctg'] = round(
                        h2h_all_time[team][opp_team]['wins'] /
                        h2h_all_time[team][opp_team]['games_played'] * 100, 2)
                else:
                    h2h_all_time[team][opp_team]['win_pctg'] = None
                if h2h_all_time[team][opp_team]['home_games_played']:
                    h2h_all_time[team][opp_team]['home_win_pctg'] = round(
                        h2h_all_time[team][opp_team]['home_wins'] /
                        h2h_all_time[team][opp_team]['home_games_played'] *
                        100, 2)
                else:
                    h2h_all_time[team][opp_team]['home_win_pctg'] = None
                if h2h_all_time[team][opp_team]['road_games_played']:
                    h2h_all_time[team][opp_team]['road_win_pctg'] = round(
                        h2h_all_time[team][opp_team]['road_wins'] /
                        h2h_all_time[team][opp_team]['road_games_played'] *
                        100, 2)
                else:
                    h2h_all_time[team][opp_team]['road_win_pctg'] = None
                if h2h_all_time[team][opp_team]['po_games_played']:
                    h2h_all_time[team][opp_team]['win_pctg_po'] = round(
                        h2h_all_time[team][opp_team]['po_wins'] /
                        h2h_all_time[team][opp_team]['po_games_played'] *
                        100, 2)
                else:
                    h2h_all_time[team][opp_team]['win_pctg_po'] = None
                if h2h_all_time[team][opp_team]['home_po_games_played']:
                    h2h_all_time[team][opp_team]['home_win_pctg_po'] = round(
                        h2h_all_time[team][opp_team]['home_po_wins'] /
                        h2h_all_time[team][opp_team]['home_po_games_played'] *
                        100, 2)
                else:
                    h2h_all_time[team][opp_team]['home_win_pctg_po'] = None
                if h2h_all_time[team][opp_team]['road_po_games_played']:
                    h2h_all_time[team][opp_team]['road_win_pctg_po'] = round(
                        h2h_all_time[team][opp_team]['road_po_wins'] /
                        h2h_all_time[team][opp_team]['road_po_games_played'] *
                        100, 2)
                else:
                    h2h_all_time[team][opp_team]['road_win_pctg_po'] = None

    tgt_h2h_path = os.path.join(tgt_dir, SEASON_HEAD2HEAD_TGT)
    open(tgt_h2h_path, 'w').write(json.dumps(h2h_all_time, indent=2))
