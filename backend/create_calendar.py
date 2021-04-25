#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import json
import pendulum

from dateutil.parser import parse

from datetime import timedelta

from ics import Calendar, Event

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

SEASON = 2020

TGT_DIR = CONFIG['tgt_processing_dir']
TGT_FILE = "del_calendar.ics"


if __name__ == '__main__':

    # loading full schedule
    schedules_src_path = os.path.join(CONFIG['tgt_processing_dir'], str(SEASON), 'full_schedule.json')
    schedules = json.loads(open(schedules_src_path).read())
    # sorting schedule by start date and time
    schedules = sorted(schedules, key=lambda s: s['start_date'])

    print("+ Creating calendar file from schedules at %s" % schedules_src_path)

    c = Calendar()

    for fixture in schedules[:]:
        e = Event()
        if fixture['start_date'] == "0000-00-00 00:00:00":
            continue
        # identifying actual start date and time
        begin = parse(fixture['start_date'])
        begin = pendulum.datetime(
            begin.year, begin.month, begin.day, hour=begin.hour, minute=begin.minute, tz='Europe/Berlin')
        # setting start and end time for event
        e.begin = str(begin)
        end = begin + timedelta(hours=3)
        e.end = str(end)
        print("+ Creating event: %s - %s on %s" % (fixture['home']['name'], fixture['guest']['name'], begin.date()))
        e.name = "%s - %s" % (fixture['home']['name'], fixture['guest']['name'])
        # adding event to calendar
        c.events.add(e)

    # writing calendar to ics file
    tgt_path = os.path.join(TGT_DIR, str(SEASON), TGT_FILE)
    with open(tgt_path, 'w', encoding='utf-8') as tgt_ics:
        tgt_ics.writelines(c)
