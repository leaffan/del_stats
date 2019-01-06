import json
import requests
from datetime import datetime
import time

#1302
#1296

BASE_URL='https://www.del.org/live-ticker/matches/'
GAME_ID=str(1296)
FILE_HOME='/player-stats-home.json'
FILE_GUEST='/player-stats-guest.json'

raw_stats = dict()
raw_stats_old = dict()
r = requests.get(BASE_URL + GAME_ID + FILE_HOME)
raw_stats_old['home'] = r.json()
r = requests.get(BASE_URL + GAME_ID + FILE_GUEST)
raw_stats_old['guest'] = r.json()


while(1):
	r = requests.get(BASE_URL + GAME_ID + FILE_HOME)
	raw_stats['home'] = r.json()
	r = requests.get(BASE_URL + GAME_ID + FILE_GUEST)
	raw_stats['guest'] = r.json()
	print('.')
	#print(raw_stats['home'][10]['statistics']['shifts'])
	#print(raw_stats['home'][2]['name'])
	for i in range (0, len(raw_stats['home'])):
		#print(str(raw_stats['home'][i]['statistics']['shifts']) + ' ' + str(raw_stats['home'][i]['statistics']['shifts']))
		if (int(raw_stats['home'][i]['statistics']['timeOnIce']) > int(raw_stats_old['home'][i]['statistics']['timeOnIce'])):
			print(str(raw_stats['home'][i]['jersey']) + ' ' + raw_stats['home'][i]['name'])
			raw_stats['home'][1]['last_shift'] = datetime.now().timestamp() * 1000;

	raw_stats_old = raw_stats.copy();	
	time.sleep(1)

print(raw_stats['home'][1]['last_shift'])