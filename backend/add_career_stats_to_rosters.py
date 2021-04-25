#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import json
import argparse

from operator import itemgetter
from collections import defaultdict

from utils import player_name_corrections

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

SKATER_INTEGERS = ['gp', 'g', 'a', 'pts', 'plus_minus', 'pim', 'ppg', 'shg', 'gwg', 'sog']

TEAMGETTER = itemgetter('team')


def combine_season_statlines(season_stat_lines):
    """
    Combines multiple season stat lines (e.g. with more than one team in a season) into a single one.
    """
    combined_statline = defaultdict(int)
    for ssl in season_stat_lines:
        for skr_int in SKATER_INTEGERS:
            combined_statline[skr_int] += ssl[skr_int]
    else:
        if combined_statline['sog'] > 0:
            combined_statline['sh_pctg'] = round(combined_statline['g'] / combined_statline['sog'] * 100, 2)
        else:
            combined_statline['sh_pctg'] = 0.
        if combined_statline['gp'] > 0:
            combined_statline['gpg'] = round(combined_statline['g'] / combined_statline['gp'], 2)
            combined_statline['apg'] = round(combined_statline['a'] / combined_statline['gp'], 2)
            combined_statline['ptspg'] = round(combined_statline['pts'] / combined_statline['gp'], 2)
        else:
            combined_statline['gpg'] = 0.
            combined_statline['apg'] = 0.
            combined_statline['ptspg'] = 0.

    return combined_statline

# TODO: overhaul this complete script


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(description='Add career stats to team roster stats.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, type=int,
        metavar='season to download data for', default=2020,
        choices=[2016, 2017, 2018, 2019, 2020],
        help="The season for which data will be processed")
    parser.add_argument(
        '-g', '--game_type', dest='game_type', required=False, default='RS',
        metavar='game type to download data for', choices=['RS', 'PO', 'MSC'],
        help="The game type for which data will be processed")

    args = parser.parse_args()
    season = args.season
    # TODO: do the following less awkward
    game_types = {
        k: v for (k, v) in CONFIG['game_types'].items() if v == args.game_type
    }
    game_type = list(game_types.keys()).pop(0)

    teams = CONFIG['teams']

    roster_stats_src_dir = os.path.join(CONFIG['base_data_dir'], 'roster_stats', str(season), str(game_type))
    goalie_stats_src_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))
    goalie_stats_src_path = os.path.join(goalie_stats_src_dir, 'del_goalie_game_stats_aggregated.json')
    goalie_stats = json.loads(open(goalie_stats_src_path).read())
    career_stats_src_path = os.path.join(CONFIG['tgt_processing_dir'], 'career_stats', 'updated_career_stats.json')
    career_stats = json.loads(open(career_stats_src_path).read())
    career_stats_per_player_src_dir = os.path.join(CONFIG['tgt_processing_dir'], 'career_stats', 'per_player')
    career_stats_against_per_player_src_dir = os.path.join(CONFIG['base_data_dir'], 'career_stats_against')

    player_game_stats_src_path = os.path.join(CONFIG['tgt_processing_dir'], str(season), 'del_player_game_stats.json')
    player_game_stats = json.loads(open(player_game_stats_src_path).read())[-1]

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], 'career_stats', 'per_team')
    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)

    # working on each team's current official roster
    for fname in os.listdir(roster_stats_src_dir):
        team = teams[int(os.path.splitext(fname)[0])]
        roster_src = os.path.join(roster_stats_src_dir, fname)
        roster = json.loads(open(roster_src).read())

        # preparing set of processed player ids to avoid retaining wrongly existing
        # duplicate entries in team roster data (as happened with MSC semi-finalists in 2020)
        plr_ids_processed = set()
        # also since duplicate entries in original data exist we have to re-create roster
        # lists to avoid those duplicate entries
        updated_roster = list()

        for plr in roster:
            plr_id = plr['id']
            # checking if player has already been processed
            if plr_id in plr_ids_processed:
                continue
            if plr_id in player_name_corrections:
                corrected_player_name = player_name_corrections[plr_id]
                if 'first_name' in corrected_player_name:
                    plr['firstname'] = corrected_player_name['first_name']
                if 'last_name' in corrected_player_name:
                    plr['surname'] = corrected_player_name['last_name']
                if 'full_name' in corrected_player_name:
                    plr['name'] = corrected_player_name['full_name']
            # calculating goalie statistics
            if plr['position'] == 'GK':
                for goalie_stat in goalie_stats:
                    # skipping pre-season tournaments
                    if goalie_stat['season_type'] == 'MSC':
                        continue
                    if goalie_stat['player_id'] == plr_id:
                        plr['statistics']['w'] = goalie_stat['w']
                        plr['statistics']['l'] = goalie_stat['l']
                        plr['statistics']['so'] = goalie_stat['so']
                        plr['statistics']['toi'] = goalie_stat['toi']
                        plr['statistics']['shots_against'] = goalie_stat['shots_against']
                        plr['statistics']['goals_against'] = goalie_stat['goals_against']
                        if plr['statistics']['shots_against']:
                            plr['statistics']['save_pctg'] = round(
                                100 - plr['statistics']['goals_against'] / plr['statistics']['shots_against'] * 100., 3)
                            plr['statistics']['gaa'] = round(
                                plr['statistics']['goals_against'] * 3600 / plr['statistics']['toi'], 2)
                        else:
                            plr['statistics']['save_pctg'] = None
                            plr['statistics']['gaa'] = None
                        break
            # retrieving current player's career stats
            curr_player_career_stats = list(filter(lambda d: plr_id == d['player_id'], career_stats))
            if len(curr_player_career_stats) == 1:
                curr_player_career_stats = curr_player_career_stats.pop(0)
            elif len(curr_player_career_stats) > 1:
                print("Multiple career stats datasets found for %s" % plr['name'])
                continue
            elif len(curr_player_career_stats) == 0:
                print("No career stats datasets found for %s" % plr['name'])
                per_player_src_path = os.path.join(career_stats_per_player_src_dir, "%d.json" % plr_id)
                if os.path.isfile(per_player_src_path):
                    curr_player_career_stats = json.loads(open(per_player_src_path).read())
            # retrieving current player's stats from last regular season
            try:
                prev_season_player_stats = list(filter(
                    lambda d: d['season'] == season - 1 and
                    d['season_type'] == 'RS', curr_player_career_stats['seasons']))
            except TypeError:
                print("No stats dataset for previous season found for %s" % plr['name'])
                prev_season_player_stats = list()
            if prev_season_player_stats:
                if len(prev_season_player_stats) > 1:
                    print("Multiple datasets from previous regular season found for player %s" % plr['name'])
                    if plr['position'] != 'GK':
                        plr['prev_season'] = dict(combine_season_statlines(prev_season_player_stats))
                    else:
                        pass
                        # TODO: take care of goalies with multiple season stat lines
                else:
                    # retaining previous season's stats (if available)
                    plr['prev_season'] = prev_season_player_stats.pop(0)
            # retrieving current player's previous DEL teams
            prev_teams = set(map(TEAMGETTER, curr_player_career_stats['seasons']))
            prev_teams.discard(team)
            plr['prev_teams'] = list(prev_teams)

            # retaining career stats
            if curr_player_career_stats and 'all' in curr_player_career_stats['career']:
                plr['career'] = curr_player_career_stats['career']['all']
            # retaining career playoff stats
            if curr_player_career_stats and 'PO' in curr_player_career_stats['career']:
                plr['career_po'] = curr_player_career_stats['career']['PO']

            # retrieving stats against other teams
            opp_team_stats = dict()
            curr_player_game_stats = list(
                filter(lambda pg: pg['player_id'] == plr_id and pg['season_type'] != 'MSC', player_game_stats))
            opp_teams = set(list(map(itemgetter('opp_team'), curr_player_game_stats)))
            for opp_team in opp_teams:
                curr_player_opp_game_stats = list(
                    filter(lambda pg: pg['opp_team'] == opp_team and pg['time_on_ice'] > 0, curr_player_game_stats))
                if curr_player_opp_game_stats:
                    single_opp_team_stats = dict()
                    single_opp_team_stats['gp'] = len(curr_player_opp_game_stats)
                    single_opp_team_stats['g'] = sum(map(itemgetter('goals'), curr_player_opp_game_stats))
                    single_opp_team_stats['a'] = sum(map(itemgetter('assists'), curr_player_opp_game_stats))
                    single_opp_team_stats['pts'] = sum(map(itemgetter('points'), curr_player_opp_game_stats))
                    single_opp_team_stats['gwg'] = sum(map(itemgetter('gw_goals'), curr_player_opp_game_stats))
                    single_opp_team_stats['pim'] = sum(map(itemgetter('pim_from_events'), curr_player_opp_game_stats))
                    opp_team_stats[opp_team] = single_opp_team_stats
            plr['opp_team_stats'] = opp_team_stats

            # calculating overall career stats against other teams
            career_against_stats_src_path = os.path.join(career_stats_against_per_player_src_dir, '%d.json' % plr_id)
            if os.path.isfile(career_against_stats_src_path):
                career_against_stats = json.loads(open(career_against_stats_src_path).read())['career_against']
            else:
                career_against_stats = dict()

            opp_team_stats_career = dict()

            for opp_team in CONFIG['teams'].values():
                single_career_opp_team_stats = defaultdict(int)
                if opp_team in career_against_stats:
                    single_career_opp_team_stats['gp'] = career_against_stats[opp_team]['games_played']
                    single_career_opp_team_stats['g'] = career_against_stats[opp_team]['goals']
                    single_career_opp_team_stats['a'] = career_against_stats[opp_team]['assists']
                    single_career_opp_team_stats['pts'] = career_against_stats[opp_team]['points']
                    single_career_opp_team_stats['gwg'] = None
                    single_career_opp_team_stats['pim'] = career_against_stats[opp_team]['pim']
                if opp_team in plr['opp_team_stats']:
                    single_career_opp_team_stats['gp'] += plr['opp_team_stats'][opp_team]['gp']
                    single_career_opp_team_stats['g'] += plr['opp_team_stats'][opp_team]['g']
                    single_career_opp_team_stats['a'] += plr['opp_team_stats'][opp_team]['a']
                    single_career_opp_team_stats['pts'] += plr['opp_team_stats'][opp_team]['pts']
                    single_career_opp_team_stats['pim'] += plr['opp_team_stats'][opp_team]['pim']
                if single_career_opp_team_stats:
                    opp_team_stats_career[opp_team] = single_career_opp_team_stats

            plr['opp_team_stats_career'] = opp_team_stats_career

            updated_roster.append(plr)
            plr_ids_processed.add(plr_id)

        tgt_path = os.path.join(tgt_dir, "%s_stats.json" % team)
        open(tgt_path, 'w').write(json.dumps(updated_roster, indent=2))
