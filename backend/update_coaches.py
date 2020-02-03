#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml

from utils import calculate_games_left_till_next_hundred

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

PRE_SEASON_COACHES_SRC = 'pre_season_coaches.json'
SEASON_COACHES_TGT = 'coaches.json'
TEAM_GAME_SRC = 'del_team_game_stats.json'
SEASON = 2019

if __name__ == '__main__':

    print("+ Updating coaches records")

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(SEASON))
    team_games_src_path = os.path.join(tgt_dir, TEAM_GAME_SRC)
    pre_season_coaches_src_path = os.path.join(tgt_dir, PRE_SEASON_COACHES_SRC)
    team_games = json.loads(open(team_games_src_path).read())
    pre_season_coaches = json.loads(open(pre_season_coaches_src_path).read())

    coaches_records = dict()

    # collecting coaches' records for current season
    for team_game in team_games[-1]:
        team = team_game['team']
        coach = team_game['coach']
        # at times coaches are missing on game sheets
        # we then look for other coaches having coached this team
        if coach is None:
            team_coaches = list(filter(
                lambda d: d['team'] == team, pre_season_coaches))
            # if just one other coach has been found assume this one also
            # coached the game in question
            if len(team_coaches) == 1:
                team_coach = team_coaches.pop()
                coach = " ".join((
                    team_coach['first_name'], team_coach['last_name']))
                print("+ No coach for %s registered, assuming %s" % (
                    team, coach))
            # not yet sure what to do otherwise
            else:
                coach = ""
                print(
                    "+ No coach for %s registered, " % team +
                    "multiple alternatives found")
        if (coach, team) not in coaches_records:
            coaches_records[(coach, team)] = dict()
            coaches_records[(coach, team)]['games_coached'] = 0
            coaches_records[(coach, team)]['wins'] = 0
            coaches_records[(coach, team)]['losses'] = 0
        coaches_records[(coach, team)]['games_coached'] += 1
        coaches_records[(coach, team)]['wins'] += team_game['w']
        coaches_records[(coach, team)]['losses'] += team_game['l']

    for coach, team in coaches_records:
        for coach_all_time in pre_season_coaches:
            # reconstructing full name to compare with data from team games
            full_name = " ".join((
                coach_all_time['first_name'], coach_all_time['last_name']
            ))
            # updating all-time record
            if coach == full_name and team == coach_all_time['team']:
                coach_all_time['games_coached'] += coaches_records[
                    (coach, team)]['games_coached']
                coach_all_time['wins'] += coaches_records[
                    (coach, team)]['wins']
                coach_all_time['losses'] += coaches_records[
                    (coach, team)]['losses']
                coach_all_time['win_pctg'] = round(
                    coach_all_time['wins'] /
                    coach_all_time['games_coached'] * 100, 2)
                coach_all_time['loss_pctg'] = round(
                    coach_all_time['losses'] /
                    coach_all_time['games_coached'] * 100, 2)
                coach_all_time['gcl'] = calculate_games_left_till_next_hundred(
                    coach_all_time['games_coached'])
                break
        # if current coach has no all-time record yet, create a new one
        else:
            # creating new all-time record
            print(
                "+ Creating new coaching-all-time record " +
                "for %s (%s)" % (coach, team))
            single_coach_all_time = dict()
            single_coach_all_time['team'] = team
            # splitting full name into first and last name naively
            first_name, last_name = coach.split()
            single_coach_all_time['first_name'] = first_name
            single_coach_all_time['last_name'] = last_name
            single_coach_all_time['games_coached'] = coaches_records[
                (coach, team)]['games_coached']
            single_coach_all_time['wins'] = coaches_records[
                (coach, team)]['wins']
            single_coach_all_time['losses'] = coaches_records[
                (coach, team)]['losses']
            single_coach_all_time['win_pctg'] = round(
                single_coach_all_time['wins'] /
                single_coach_all_time['games_coached'] * 100, 2)
            single_coach_all_time['loss_pctg'] = round(
                single_coach_all_time['losses'] /
                single_coach_all_time['games_coached'] * 100, 2)
            single_coach_all_time[
                'gcl'] = calculate_games_left_till_next_hundred(
                    single_coach_all_time['games_coached'])
            pre_season_coaches.append(single_coach_all_time)

    tgt_coaches_path = os.path.join(tgt_dir, SEASON_COACHES_TGT)
    open(tgt_coaches_path, 'w').write(json.dumps(pre_season_coaches, indent=2))
