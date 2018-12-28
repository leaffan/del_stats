#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

import requests
from shapely.geometry import Point

import rink_dimensions as rd


BASE_URL = 'https://www.del.org/live-ticker'
SHOTS_SUFFIX = "visualization/shots/%d.json"
GAME_SRC = 'del_games.json'
SHOTS_DATA_TGT = 'del_shots.json'
TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

SHOT_RESULTS = {
    1: 'on_goal', 2: 'missed', 3: 'blocked', 4: 'on_goal'
}

if __name__ == '__main__':

    # setting up source and target paths
    src_path = os.path.join(TGT_DIR, GAME_SRC)
    tgt_path = os.path.join(TGT_DIR, SHOTS_DATA_TGT)

    # loading games
    games = json.loads(open(src_path).read())

    # preparing container for all shots
    all_shots = list()

    for game in games[:]:
        print("+ Working on game %d" % game['game_id'])

        # retrieving raw shot data
        shots_path = SHOTS_SUFFIX % game['game_id']
        shots_url = "%s/%s" % (BASE_URL, shots_path)
        r = requests.get(shots_url)
        match_data = r.json()

        for shot in match_data['match']['shots'][:]:

            # converting arbitrary coordinates to actual coordinates in meters
            x = rd.X_TO_M * shot['coordinate_x']
            y = rd.Y_TO_M * shot['coordinate_y']

            # constructing shot location
            shot_pnt = Point(x, y)
            # calculating shot distance
            if shot['team_id'] == game['road_id']:
                shot['team'] = game['road_abbr']
                dst = rd.HOME_GOAL.distance(shot_pnt)
            elif shot['team_id'] == game['home_id']:
                shot['team'] = game['home_abbr']
                dst = rd.ROAD_GOAL.distance(shot_pnt)
            # determining target and outcome of shot
            shot['target_type'] = SHOT_RESULTS[shot['match_shot_resutl_id']]
            if shot['match_shot_resutl_id'] == 4:
                shot['scored'] = True
            else:
                shot['scored'] = False
            del(shot['match_shot_resutl_id'])
            if 'real_date' in shot:
                del(shot['real_date'])

            # determining shot zone
            for poly_name, poly in rd.polygons:
                if poly.intersects(shot_pnt):
                    shot['shot_zone'] = poly_name[5:]
                    break

            # adding new values to shot item
            shot['distance'] = round(dst, 2)
            shot['x'] = round(x, 2)
            shot['y'] = round(y, 2)
            shot['game_id'] = game['game_id']
            shot['schedule_game_id'] = game['schedule_game_id']

            all_shots.append(shot)

    open(tgt_path, 'w').write(json.dumps(all_shots, indent=2, default=str))
