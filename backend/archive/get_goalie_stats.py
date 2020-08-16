#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import yaml
import requests
import urllib.parse

from datetime import datetime

from lxml import html

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..', 'config.yml')))

user = CONFIG['del_archive_user']
pwd = CONFIG['del_archive_pass']

TOP_GOALIES_URL = "/".join(
    (CONFIG['del_archive_base_url'], "toptorhueter_%d.html"))
EP_SEARCH_URL = 'https://www.eliteprospects.com/search/player?q=%s'

TGT_STATS_TPL = 'goalie_stats'
TGT_PROCESSED_IDS = 'goalies_done.json'


def retrieve_ep_plr_id(del_name, del_dob):
    ep_search_url = EP_SEARCH_URL % "+".join(del_name.split()).lower()

    er = requests.get(ep_search_url)
    edoc = html.fromstring(er.text)

    trs = edoc.xpath("//tbody//td[@class='name']/ancestor::tr")

    if len(trs) == 1:
        tr = trs.pop()
    else:
        for tr in trs:
            ep_name_pos = tr.xpath("td[@class='name']/span/a/text()")[0]
            ep_name, pos = [x.strip() for x in ep_name_pos.rsplit(maxsplit=1)]
            if pos != '(G)':
                continue
            ep_dob = tr.xpath("td[@class='date-of-birth']/span[1]/text()")
            ep_dob = datetime.strptime(ep_dob[0], '%Y-%m-%d').date()

            if ep_name == del_name and ep_dob == del_dob:
                break

    ep_plr_id = "/".join(
        tr.xpath("td[@class='name']/span/a/@href")[0].split("/")[-2:])

    return urllib.parse.unquote(ep_plr_id)


def get_goalie_stats_for_season(season_id):

    url = TOP_GOALIES_URL % season_id
    r = requests.get(url, auth=(user, pwd))
    doc = html.fromstring(r.text)

    season_info = doc.xpath("//button[@id='btnGroupDrop1']/text()")
    try:
        season = int(season_info[0].split()[-1].split("/")[0])
    except Exception:
        print("+ Unable to retrieve season from page content")
        return
    season = int(season_info[0].split()[-1].split("/")[0])
    season_type = season_info[1].strip()

    print("+ Retrieving goalie stats for %d (%s)" % (season, season_type))

    tds = doc.xpath("//table[@id='myTable']/tbody/tr/td[2]")

    for td in tds[:]:

        goalie = dict()

        name = td.xpath("a/text()")[0]
        link = td.xpath("a/@href")[0]
        plr_id = link.replace(".html", "").split("_")[-1]

        goalie['name'] = name
        goalie['del_archive_id'] = plr_id

        if plr_id in goalie_ids_processed:
            continue

        print("+ Working on stats for %s" % goalie['name'])

        plr_url = "/".join((CONFIG['del_archive_base_url'], link))
        r = requests.get(plr_url, auth=(user, pwd))
        gdoc = html.fromstring(r.text)

        try:
            dob = gdoc.xpath(
                "//td[text() = 'Geburtsdatum:']/following-sibling::td/text()")
            dob = dob[0].split("-")[0].strip()
            dob_dt = datetime.strptime(dob, '%d.%m.%Y').date()
            ep_id = retrieve_ep_plr_id(name, dob_dt)
            print("-> EP ID: %s" % ep_id)
        except Exception:
            ep_id = ''
        finally:
            goalie['ep_id'] = ep_id

        stats_trs = gdoc.xpath(
            "//h3[text() = 'Statistik']/ancestor::div/table[1]/tbody/tr")

        goalie['stats'] = list()
        for stats_tr in stats_trs:

            season_stats = dict()

            season_info = stats_tr.xpath("td[1]/text()")
            if not season_info:
                continue
            _, season, season_type = season_info[0].replace("-", "").split()
            season = int(season.split("/")[0])
            if season_type == 'Hauptrunde':
                season_type = 'RS'
            elif season_type == 'Playoffs':
                season_type = 'PO'
            team = stats_tr.xpath("td[2]/a/text()").pop()

            # archived goalie stats from before 1999 are unusable
            if season < 1999:
                continue

            season_stats['season'] = season
            season_stats['season_type'] = season_type
            season_stats['team'] = team

            games_played = int(stats_tr.xpath("td[3]/text()").pop())

            if not games_played:
                continue

            (
                games_played, minutes, wins, ties, losses, shutouts,
                goals_against, gaa, saves, sv_pctg
            ) = stats_tr.xpath("td[starts-with(@class,'acenter')]/text()")

            season_stats['games_played'] = int(games_played)
            season_stats['toi'] = minutes
            mins, secs = [int(x) for x in season_stats['toi'].split(":")]
            season_stats['toi_seconds'] = mins * 60 + secs
            season_stats['wins'] = int(wins)
            season_stats['ties'] = int(ties)
            season_stats['losses'] = int(losses)
            season_stats['shutouts'] = int(shutouts)
            season_stats['goals_against'] = int(goals_against)
            season_stats['saves'] = int(saves)
            season_stats['shots_against'] = (
                season_stats['goals_against'] + season_stats['saves'])
            season_stats['gaa'] = float(gaa.replace(",", "."))
            season_stats['sv_pctg'] = float(sv_pctg[:-1].replace(",", "."))

            if season < 2003:
                season_stats['goals_against'] = int(
                    season_stats['goals_against'] / 2)
                season_stats['saves'] = int(season_stats['saves'] / 2)
                season_stats['shots_against'] = (
                    season_stats['goals_against'] + season_stats['saves'])
                season_stats['gaa'] = round(
                    season_stats['goals_against'] * 3600 /
                    season_stats['toi_seconds'], 2)
                season_stats['sv_pctg'] = round(
                    100 - season_stats['goals_against'] /
                    season_stats['shots_against'] * 100., 1)

            goalie['stats'].append(season_stats)

        all_goalie_stats.append(goalie)
        goalie_ids_processed.append(plr_id)

        time.sleep(0.5)


if __name__ == '__main__':

    if os.path.isfile("%s.json" % TGT_STATS_TPL):
        all_goalie_stats = json.loads(open("%s.json" % TGT_STATS_TPL).read())
    else:
        all_goalie_stats = list()
    if os.path.isfile(TGT_PROCESSED_IDS):
        goalie_ids_processed = json.loads(open(TGT_PROCESSED_IDS).read())
    else:
        goalie_ids_processed = list()

    # for season_id in range(25, 21, -1):
    for season_id in range(45, 16, -1):
        get_goalie_stats_for_season(season_id)

        open("%s.json" % TGT_STATS_TPL, 'w').write(
            json.dumps(all_goalie_stats, indent=2))
        open(TGT_PROCESSED_IDS, 'w').write(
            json.dumps(goalie_ids_processed, indent=2))
