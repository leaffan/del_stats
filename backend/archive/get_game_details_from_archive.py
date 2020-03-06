#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import yaml
import requests

from collections import defaultdict
from lxml import html

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

GAME_URL = "/".join((CONFIG['del_archive_base_url'], "game_%d_%d.html"))

SRC_DIR = os.path.join(CONFIG['base_data_dir'], 'archive')

user = CONFIG['del_archive_user']
pwd = CONFIG['del_archive_pass']

games_per_season = defaultdict(list)

for f in os.listdir(SRC_DIR)[1:]:
    if not f.startswith("games_"):
        continue

    season = int(f.replace(".json", "").split("_")[-1])

    games = json.loads(open(os.path.join(SRC_DIR, f)).read())
    print("+ Loaded %d games from %d season" % (len(games), season))

    game_infos = list()

    cnt = 0
    last_percent = 0

    t0 = time.time()
    for game in games[:]:
        cnt += 1
        percent = int(cnt / len(games) * 100)
        if percent % 5 == 0 and percent > last_percent:
            t1 = time.time()
            td = t1 - t0
            print("\t+ %d%% of games processed (%g s)" % (percent, td))
            last_percent = percent
            t0 = t1

        game['arena'] = None
        game['attendance'] = None
        url = GAME_URL % (game['season_id'], game['game_id'])
        r = requests.get(url, auth=(user, pwd))
        doc = html.fromstring(r.text)

        if game['game_time'] is None:
            score_date_attendance = doc.xpath(
                "//div[@class='col-12 text-center']/text()")
            game_time = score_date_attendance[2].strip().split(",")[-1]
            game['game_time'] = game_time.replace("Uhr", "").strip()

        trs = doc.xpath(
            "//h3[text()='Weitere Informationen']/" +
            "following-sibling::table/tbody/tr")
        for tr in trs:
            tds = tr.xpath("td/text()")
            if len(tds) < 2:
                continue
            key, val = tds
            if key == 'Arena:':
                game['arena'] = val
            if key == 'Besucherzahl:':
                game['attendance'] = int(val)

        game_infos.append(game)
        time.sleep(0.2)

    games_per_season[season] = game_infos

for season in games_per_season:
    tgt_file = "games_%d.json" % season
    tgt_path = os.path.join(
        CONFIG['base_data_dir'], 'archive_game_info', tgt_file)
    open(tgt_path, 'w').write(
        json.dumps(games_per_season[season], indent=2))
