app.controller('previewController', function($scope, $http, $routeParams, $location, $anchorScroll, $timeout, $sce, svc) {
    $scope.svc = svc;
    $scope.Math = window.Math;
    $scope.season = $routeParams.season;
    $scope.current_game_id = $routeParams.game_id;
    $scope.previous_stats_home = false;
    $scope.previous_stats_road = false;

    $scope.roster_stats_display_item = 'current';
    // $scope.roster_stats_display_item = 'previous';
    // $scope.roster_stats_display_item = 'career_against';

    $scope.loaded_data_from_last_season = false;

    $scope.regional_display = 'active';
    $scope.league_display = '';

    $scope.toggle_new_stuff = true;

    $scope.divisions = ['Nord', 'Süd']
    $scope.divisions_per_team = {
        'WOB': 'Nord', 'EBB': 'Nord', 'BHV': 'Nord', 'DEG': 'Nord', 'KEC': 'Nord', 'IEC': 'Nord', 'KEV': 'Nord',
        'MAN': 'Süd', 'SWW': 'Süd', 'ING': 'Süd', 'STR': 'Süd', 'RBM': 'Süd', 'NIT': 'Süd', 'AEV': 'Süd',
    };

    // loading current game data from full schedule
    $http.get('data/'+ $scope.season + '/full_schedule.json').then(function (res) {
        $scope.games = res.data;
        $scope.games.forEach(game => {
            game['game_date'] = moment(game['start_date']);
        });
        // finding current game by game_id
        $scope.current_game = $scope.games.find(function(game) {
            return game['game_id'] == $scope.current_game_id;
        });
        $scope.is_playoff_game = !svc.isNumeric($scope.current_game.round);
        // retrieving the date before game date
        // moment needs to be cloned first (by calling moment() on it) before subtracting a day
        $scope.previous_date = moment($scope.current_game['game_date']).subtract(1, 'days');
        $scope.current_home_team = $scope.current_game.home.name;
        $scope.current_road_team = $scope.current_game.guest.name;
        $scope.current_season = parseInt($scope.current_game.season);
        $scope.current_season = $scope.current_season.toString() + "/" + ($scope.current_season + 1 - 2000).toString();
        $scope.current_home_team_fixtures = $scope.games.filter(function(value, index, arr) {
            return value['status'] == 'BEFORE_MATCH' && ($scope.current_game.home.name == value['home']['name'] || $scope.current_game.home.name == value['guest']['name']);
        });
        $scope.current_home_vs_road_fixtures = $scope.current_home_team_fixtures.filter(function(value, index, arr) {
            return value['home']['name'] == $scope.current_game.guest.name || value['guest']['name'] == $scope.current_game.guest.name;
    	});
        $scope.current_home_team_home_fixtures_cnt = ($scope.current_home_team_fixtures.filter(fixture => $scope.current_game.home.name == fixture['home']['name'])).length;
        $scope.current_home_team_road_fixtures_cnt = ($scope.current_home_team_fixtures.filter(fixture => $scope.current_game.home.name == fixture['guest']['name'])).length;
        $scope.current_road_team_fixtures = $scope.games.filter(function(value, index, arr) {
            return value['status'] == 'BEFORE_MATCH' && ($scope.current_game.guest.name == value['home']['name'] || $scope.current_game.guest.name == value['guest']['name']);
        });
        $scope.current_road_vs_home_fixtures = $scope.current_road_team_fixtures.filter(function(value, index, arr) {
            return value['home']['name'] == $scope.current_game.home.name || value['guest']['name'] == $scope.current_game.home.name;
        });
        $scope.current_road_team_home_fixtures_cnt = ($scope.current_road_team_fixtures.filter(fixture => $scope.current_game.guest.name == fixture['home']['name'])).length;
        $scope.current_road_team_road_fixtures_cnt = ($scope.current_road_team_fixtures.filter(fixture => $scope.current_game.guest.name == fixture['guest']['name'])).length;
        $http.get('data/career_stats/per_team/'+ $scope.current_game.home.shortcut + '_stats.json').then(function (res) {
            $scope.home_career_stats = res.data;
            console.log($scope.home_career_stats[10]);
        });
        $http.get('data/career_stats/per_team/'+ $scope.current_game.guest.shortcut + '_stats.json').then(function (res) {
            $scope.road_career_stats = res.data;
        });
        // loading stats from external json file
        $http.get('data/'+ $scope.season + '/del_team_game_stats.json').then(function (res) {
            $scope.last_modified = res.data[0];
            $scope.team_stats = res.data[1];
            // retrieving regular season team statistics
            $scope.full_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS');
            $scope.home_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS', 'home');
            $scope.road_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS', 'road');

            if ($scope.full_season_stats.length == 0 || $scope.current_game.round == 1) {
                $http.get('data/'+ ($scope.season - 1) + '/del_team_game_stats.json').then(function (res) {
                    $scope.team_stats = res.data[1];
                    $scope.full_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS');
                    $scope.home_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS', 'home');
                    $scope.road_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS', 'road');
                });
            };

            if ($scope.is_playoff_game) {
                $scope.full_playoffs_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'PO');
                $scope.home_playoffs_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'PO', 'home');
                $scope.road_playoffs_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'PO', 'road');
            }
            $scope.game_log_home = $scope.team_stats.filter(function(value, index, arr) {
                // returning only regular season games of current home team
                // return value['season_type'] == 'RS' && value['team'] == $scope.current_game.home.shortcut;
                // returning all games of current home team
                return value['team'] == $scope.current_game.home.shortcut;
            });
            // toggling default display of last season's player stats if no regular season games have been played so far
            if ($scope.game_log_home.filter(game => game.season_type != 'MSC').length == 0) {
                $scope.previous_stats_home = true;
            }
            $scope.game_log_road = $scope.team_stats.filter(function(value, index, arr) {
                // returning only regular season games of current road team
                // return value['season_type'] == 'RS' && value['team'] == $scope.current_game.guest.shortcut;
                // returning all games of current home team
                return value['team'] == $scope.current_game.guest.shortcut;
            });
            // toggling default display of last season's player stats if no regular season games have been played so far
            if ($scope.game_log_road.filter(game => game.season_type != 'MSC').length == 0) {
                $scope.previous_stats_road = true;
            }
            $scope.game_log_home_vs_road = $scope.game_log_home.filter(function(value, index, arr) {
                return value['opp_team'] == $scope.current_game.guest.shortcut;
            });

            // if head-to-head game log is empty, i.e. no games between the current teams this season
            // then load it from previous season
            // if ($scope.game_log_home_vs_road.length == 0) {
            $http.get('data/'+ ($scope.season - 1) + '/del_team_game_stats.json').then(function (res) {
                $scope.team_stats_last_season = res.data[1];
                $scope.game_log_home_vs_road_last_season = $scope.team_stats_last_season.filter(function(value, index, arr) {
                    return value['team'] == $scope.current_game.home.shortcut && value['opp_team'] == $scope.current_game.guest.shortcut;
                });
                // $scope.game_log_home_vs_road = $scope.game_log_home_vs_road.concat($scope.game_log_home_vs_road_last_season);
            });
            // }

            $scope.game_log_road_vs_home = $scope.game_log_road.filter(function(value, index, arr) {
                return value['opp_team'] == $scope.current_game.home.shortcut;
            });

            // if head-to-head game log is empty, i.e. no games between the current teams this season
            // then load it from previous season
            // if ($scope.game_log_road_vs_home.length == 0) {
            $http.get('data/'+ ($scope.season - 1) + '/del_team_game_stats.json').then(function (res) {
                $scope.team_stats_last_season = res.data[1];
                $scope.game_log_road_vs_home_last_season = $scope.team_stats_last_season.filter(function(value, index, arr) {
                    return value['team'] == $scope.current_game.guest.shortcut && value['opp_team'] == $scope.current_game.home.shortcut;
                });
            });
            // }
        });

        // loading playoff series from external json file
        $http.get('data/po_series.json').then(function (res) {
            $scope.po_series = res.data;
            $scope.filtered_po_series = $scope.filterPlayoffSeries($scope.po_series);
            $scope.series_total_games= svc.getFilteredTotal($scope.filtered_po_series, 'games_played', null); 
            $scope.series_wins = $scope.filtered_po_series.filter(series => series.series_win === 1).length;
            $scope.series_losses = $scope.filtered_po_series.filter(series => series.series_loss === 1).length;
        });

        // loading player scoring streaks from external json file
        $http.get('data/'+ $scope.season + '/del_slumps_loose.json').then(function (res) {
            $scope.slumps = res.data.filter(slump => (slump.team == $scope.current_game.home.shortcut || slump.team == $scope.current_game.guest.shortcut));;
        });
    
    });

    // loading game facts
    $http.get('data/'+ $scope.season + '/facts.json').then(function (res) {
        facts = res.data;
        $scope.facts = res.data[$scope.current_game_id] || {};
        // trusting each fact's html source
        for (var key in $scope.facts) {
            if ($scope.facts.hasOwnProperty(key)) {
                $scope.facts[key] = $sce.trustAsHtml($scope.facts[key]);
            }
        }
    });

    // retrieving previous year's attendance from external file
    $http.get('./data/' + $scope.season + '/dates_attendance.json').then(function (res) {
        $scope.avg_attendance_last_season = res.data['avg_attendance_last_season'];
    });

    $scope.sorting_config = {
        'h2h_recent_table': ['game_date'],
        'game_log_table': ['game_date'],
        'standings': ['-pts_per_game', '-points', '-score_diff', '-score'],
        'powerplay_standings': ['-pp_pctg', '-pp_goals', 'opp_sh_goals'],
        'penalty_killing_standings': ['-pk_pctg', 'opp_pp_goals', '-sh_goals'],
        'goals_by_period_1_standings': ['-goals_1', '-goals_diff_1'],
        'goals_by_period_2_standings': ['-goals_2', '-goals_diff_2'],
        'goals_by_period_3_standings': ['-goals_3', '-goals_diff_3'],
        'faceoffs_standings': ['-faceoff_pctg', '-faceoffs_won'],
        'shots_for_standings': ['-shots_on_goal', '-goals'],
        'shots_on_goal_for_zones_standings': ['-sl_og_p', '-sl_og'],
        'shots_on_goal_against_zones_standings': ['sl_og_p_a', 'sl_og_a'],
        'attendance_standings': ['-util_capacity', '-attendance'],
        'penalties_standings': ['pim_per_game', 'penalties'],
        'scoring_rankings': ['-points', '-points_per_game', '-goals', '-primary_points'],
        'scoring_powerplay_rankings': ['-pp_points', '-pp_points_per_60', '-pp_goals'],
        'scoring_shorthanded_rankings': ['-sh_points', '-sh_points_per_60', '-sh_goals'],
        'plr_time_on_ice_shift_rankings': ['-time_on_ice_per_game', '-time_on_ice_seconds'],
        'plr_on_goal_shot_zones_rankings': ['-shots_on_goal', '-slot_on_goal'],
        'plr_faceoffs_rankings': ['-faceoff_pctg', '-faceoffs'],
        'plr_blocks_rankings': ['-blocked_shots', '-blocked_shots_per_game'],
        'plr_missed_rankings': ['-shots_missed', '-shots_missed_per_game'],
        'plr_plus_minus_pos_rankings': ['-plus_minus', 'games_played'],
        'plr_plus_minus_neg_rankings': ['plus_minus', 'games_played'],
        'goalie_stats_rankings': ['-save_pctg', 'gaa'],
        'goalie_zone_stats_rankings': ['-save_pctg_slot', 'sa_slot'],
        'rosters': ['jersey'],
        'coaches_rankings': ['-win_pctg', '-wins'],
        'streaks_goals': ['-length', '-goals'],
        'streaks_assists': ['-length', '-assists'],
        'streaks_points': ['-length', '-points'],
        'slumps_goals': ['-length', '-to_date'],
        'slumps_points': ['-length', '-to_date'],
        'slot_shots_goals': ['-sl_og']
    }

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/preview_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // loading teams from external json file
    $http.get('./js/teams.json').then(function (res) {
        // only retaining teams valid for current season
        $scope.teams = res.data.filter(team => team.valid_from <= $scope.season && team.valid_to >= $scope.season);
        // creating lookup structures...
        // ...for team locations
        $scope.team_location_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.location}), {});
        // ...for playoff participation indicator
        // $scope.team_playoff_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.po}), {});
        // ...for team colors
        $scope.team_color_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.full_name]: key.colors}), {});
    });
    
    // loading arenas from external json file
    $http.get('data/arenas.json').then(function (res) {
        $scope.arenas = res.data;
    });

    // loading h2h data from external json file
    $http.get('data/'+ $scope.season + '/h2h.json').then(function (res) {
        $scope.h2h = res.data;
    });
    
    // loading player scoring streaks from external json file
    $http.get('data/'+ $scope.season + '/del_streaks_loose.json').then(function (res) {
        $scope.streaks = res.data;
    });

    // loading coaches from external json file
    $http.get('data/'+ $scope.season + '/coaches.json').then(function (res) {
        $scope.coaches = res.data;
    });

    // loading goalie stats from external json file
    $http.get('data/'+ $scope.season + '/del_goalie_game_stats.json').then(function (res) {
        $scope.goalie_stats = res.data.filter(game => game.season_type != 'MSC');
        if ($scope.goalie_stats.length == 0 || $scope.current_game.round == 1) {
            $http.get('data/'+ ($scope.season - 1) + '/del_goalie_game_stats.json').then(function (res) {
                $scope.goalie_stats = res.data.filter(game => game.season_type != 'MSC');
                $scope.full_goalie_stats = $scope.getGoalieSeasonStats($scope.goalie_stats, $scope.current_game);
            });
        } else {
            $scope.full_goalie_stats = $scope.getGoalieSeasonStats($scope.goalie_stats, $scope.current_game);
        }
    });

    $scope.getGoalieSeasonStats = function(goalie_games, current_game) {
        if (goalie_games === undefined)
            return [];
        // not including current team game element if game date was after the previewed game
        goalie_games_before_current_game = goalie_games.filter(function(gg) {
            return moment(gg['game_date']).diff(current_game['game_date'], 'days') < 0;
        });
        // preparing container for goalie stats
        goalie_stats = {
            'full': {}, 'home': {}, 'road': {}
        }
        goalie_games_before_current_game.forEach(goalie_game => {
            goalie_id = goalie_game['goalie_id'];
            if (!goalie_stats['full'][goalie_id]) {
                ['full', 'home', 'road'].map(key => {
                    goalie_stats[key][goalie_id] = {};
                    goalie_stats[key][goalie_id]['full_name'] = goalie_game['first_name'] + ' ' + goalie_game['last_name'];
                    goalie_stats[key][goalie_id]['position'] = goalie_game['position'];
                    goalie_stats[key][goalie_id]['team'] = goalie_game['team'];
                    $scope.svc.goalie_stats_to_aggregate().forEach(category => {
                        goalie_stats[key][goalie_id][category] = 0;
                    });
                });
            };
            $scope.svc.goalie_stats_to_aggregate().forEach(category => {
                goalie_stats['full'][goalie_id][category] += goalie_game[category];
                goalie_stats[goalie_game['home_road']][goalie_id][category] += goalie_game[category];
            });
        });

        full_goalie_stats = [];

        Object.values(goalie_stats['full']).forEach(element => {
            if (element['shots_against'] > 0) {
                element['save_pctg'] = (1 - (element['goals_against'] / element['shots_against'])) * 100;
            } else {
                element['save_pctg'] = 0.;
            }
            if (element['toi']) {
                element['gaa'] = (element['goals_against'] * 3600.) / element['toi'];
            } else {
                element['gaa'] = parseFloat(0);
            }
            // calculating save percentages by shot zone
            if (element['sa_slot']) {
                element['save_pctg_slot'] = (1 - element['ga_slot'] / element['sa_slot']) * 100.;
            } else {
                element['save_pctg_slot'] = null;
            }
            if (element['sa_left']) {
                element['save_pctg_left'] = (1 - element['ga_left'] / element['sa_left']) * 100.;
            } else {
                element['save_pctg_left'] = null;
            }
            if (element['sa_right']) {
                element['save_pctg_right'] = (1 - element['ga_right'] / element['sa_right']) * 100.;
            } else {
                element['save_pctg_right'] = null;
            }
            if (element['sa_blue_line']) {
                element['save_pctg_blue_line'] = (1 - element['ga_blue_line'] / element['sa_blue_line']) * 100.;
            } else {
                element['save_pctg_blue_line'] = null;
            }
            full_goalie_stats.push(element);
        });

        $scope.max_goalie_games_played = Math.max.apply(Math, full_goalie_stats.map(function(o) { return o.games_played; }));
        $scope.goalie_games_at_least_played = Math.ceil($scope.max_goalie_games_played / 3);

        return full_goalie_stats;
    }

	$scope.readCSV = function(season_of_interest) {
		// http get request to read CSV file content
        $http.get('data/' + season_of_interest + '/del_player_game_stats.csv').then($scope.processData);
	};

	$scope.processData = function(allText) {
        // split content based on new line
		var allTextLines = allText.data.split(/\r\n|\n/);
		var headers = allTextLines[0].split(';');
		var lines = [];

		for ( var i = 0; i < allTextLines.length; i++) {
			// split content based on separator
			var data = allTextLines[i].split(';');
			if (data.length == headers.length) {
				var tarr = [];
				for ( var j = 0; j < headers.length; j++) {
                    tarr.push(data[j]);
				}
				lines.push(tarr);
			}
        }
        var headers = lines[0];
        $scope.player_games = lines.slice(1).map(function(line) {
            return line.reduce(function(player_game, value, i) {
                if ($scope.svc.player_stats_to_aggregate().indexOf(headers[i]) !== -1) {
                    player_game[headers[i]] = parseInt(value);
                } else if ($scope.svc.player_float_stats_to_aggregate().indexOf(headers[i]) !== -1 ) {
                    player_game[headers[i]] = parseFloat(value);
                } else if (headers[i] == 'u23') {
                    if (value == 'True') {
                        player_game[headers[i]] = true;
                    } else {
                        player_game[headers[i]] = false;
                    }
                } else {
                    player_game[headers[i]] = value;
                }
                return player_game;
            }, {})
        });
        // grouping retrieved player games by season type
        player_games_grouped_by_season_type = groupBy($scope.player_games, 'season_type');
        if (!$scope.loaded_data_from_last_season) {
            // if no regular season games have been played previously or we're in round one...
            if (!('RS' in player_games_grouped_by_season_type) || $scope.current_game.round == 1) {
                // loading data from previous season
                $scope.readCSV($scope.season - 1);
                // memorize that we've already loaded data from last season
                $scope.loaded_data_from_last_season = true;
            }
        }        
        if ('RS' in player_games_grouped_by_season_type) {
            // retrieving regular season player stats from before current game
            full_player_stats = $scope.getPlayerSeasonStats(player_games_grouped_by_season_type['RS'], $scope.current_game);
            $scope.full_season_player_stats = Object.values(full_player_stats['full']);
        } else {
            $scope.full_season_player_stats = [];
        }
        // checking whether we're looking at a playoff game
        if ($scope.is_playoff_game) {
            // if playoff games have been played previously...
            if ('PO' in player_games_grouped_by_season_type) {
                // retrieving playoff player stats from before current game
                full_playoffs_player_stats = $scope.getPlayerSeasonStats(player_games_grouped_by_season_type['PO'], $scope.current_game);
                $scope.full_playoffs_player_stats = Object.values(full_playoffs_player_stats['full']);
            }
            else {
                $scope.full_playoffs_player_stats = [];
            }
        }
	};

    $scope.readCSV($scope.season);

    var groupBy = function(xs, key) {
        return xs.reduce(function(rv, x) {
            (rv[x[key]] = rv[x[key]] || []).push(x);
            return rv;
        }, {});
    };

    $scope.getPlayerSeasonStats = function(player_games, current_game) {
        if (player_games === undefined)
            return [];
        // not including current team game element if game date was after the previewed game
        player_games_before_current_game = player_games.filter(function(pg) {
            return moment(pg['game_date']).diff(current_game['game_date'], 'days') < 0;
        });
        // preparing container for player stats
        player_stats = {
            'full': {}, 'home': {}, 'road': {}
        }
        player_games_before_current_game.forEach(player_game => {
            player_id = player_game['player_id'];
            if (!player_stats['full'][player_id]) {
                ['full', 'home', 'road'].map(key => {
                    player_stats[key][player_id] = {};
                    player_stats[key][player_id]['full_name'] = player_game['first_name'] + ' ' + player_game['last_name'];
                    player_stats[key][player_id]['position'] = player_game['position'];
                    player_stats[key][player_id]['team'] = player_game['team'];
                    $scope.svc.player_stats_to_aggregate().forEach(category => {
                        player_stats[key][player_id][category] = 0;
                    });
                });
            };
            $scope.svc.player_stats_to_aggregate().forEach(category => {
                player_stats['full'][player_id][category] += player_game[category];
                player_stats[player_game['home_road']][player_id][category] += player_game[category];
            });
        });

        Object.values(player_stats['full']).forEach(element => {
            // calculating points per game
            if (element['games_played']) {
                element['points_per_game'] = parseFloat((element['points'] / (element['games_played'])).toFixed(2));
            } else {
                element['points_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating shooting percentage
            if (element['shots_on_goal']) {
                element['shot_pctg'] = parseFloat(((element['goals'] / element['shots_on_goal']) * 100).toFixed(2));
            } else {
                element['shot_pctg'] = parseFloat((0).toFixed(2));
            }
            if (element['faceoffs']) {
                element['faceoff_pctg'] = parseFloat(((element['faceoffs_won'] / element['faceoffs']) * 100).toFixed(2));
            } else {
                element['faceoff_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating time on ice and shifts per game
            if (element['games_played']) {
                element['time_on_ice_per_game'] = (element['time_on_ice'] / element['games_played']);
                element['time_on_ice_pp_per_game'] = (element['time_on_ice_pp'] / element['games_played']);
                element['time_on_ice_sh_per_game'] = (element['time_on_ice_sh'] / element['games_played']);
                element['shifts_per_game'] = element['shifts'] / element['games_played'];
            } else {
                element['time_on_ice_per_game'] = parseFloat((0).toFixed(2));
                element['time_on_ice_pp_per_game'] = parseFloat((0).toFixed(2));
                element['time_on_ice_sh_per_game'] = parseFloat((0).toFixed(2));
                element['shifts_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating shot-on-goal zone percentages
            if (element['shots_on_goal']) {
                element['slot_on_goal_pctg'] = (element['slot_on_goal'] / element['shots_on_goal']) * 100.; 
                element['left_on_goal_pctg'] = (element['left_on_goal'] / element['shots_on_goal']) * 100.; 
                element['right_on_goal_pctg'] = (element['right_on_goal'] / element['shots_on_goal']) * 100.; 
                element['blue_line_on_goal_pctg'] = (element['blue_line_on_goal'] / element['shots_on_goal']) * 100.; 
            } else {
                element['slot_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
                element['left_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
                element['right_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
                element['blue_line_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
            }
            // calculating blocked/missed shots per game
            if (element['games_played']) {
                element['blocked_shots_per_game'] = (element['blocked_shots'] / element['games_played']);
                element['shots_missed_per_game'] = (element['shots_missed'] / element['games_played']);
            } else {
                element['blocked_shots_per_game'] = 0;
                element['shots_missed_per_game'] = 0;
            }
            // calculating powerplay points percentage
            if (element['points']) {
                element['pp_pts_pctg'] = (element['pp_points'] / element['points']) * 100.;
            } else {
                element['pp_pts_pctg'] = 0;
            }
        });
        return player_stats;
    };

    $scope.getSeasonStats = function(stats, current_game, season_type, home_road_type) {
        full_team_stats = {};
        if (stats === undefined)
            return full_team_stats;

        // setting up team stats by creating stub list with all valid teams (just in case any team hasn't
        // played a game yet)
        $scope.teams.forEach(team => {
            team_abbr = team['abbr'];
            if (!full_team_stats[team_abbr]) {
                full_team_stats[team_abbr] = {};
                full_team_stats[team_abbr]['team'] = team_abbr;
                full_team_stats[team_abbr]['division'] = $scope.divisions_per_team[team_abbr];
                full_team_stats[team_abbr]['capacity'] = 0;
                $scope.svc.stats_to_aggregate().forEach(category => {
                    full_team_stats[team_abbr][category] = 0;
                });
            };
        });
        stats.forEach(team_game => {
            team = team_game['team'];
            game_date = moment(team_game['game_date']);
            // don't include current team game element if game date was after the previewed game
            if (game_date.diff(current_game['game_date'], 'days') >= 0)
                return;
            if (team_game['season_type'] != season_type)
                return;
            // only retain home/road games if specified
            if (home_road_type && home_road_type != team_game['home_road'])
                return;
            $scope.svc.stats_to_aggregate().forEach(category => {
                full_team_stats[team][category] += team_game[category];
            });
        });

        full_team_stats = Object.values(full_team_stats);

        full_team_stats.forEach(team_game => {
            // calculating score and goal differentials
            team_game['score_diff'] = team_game['score'] - team_game['opp_score'];
            team_game['goals_diff'] = team_game['goals'] - team_game['opp_goals'];
            team_game['goals_diff_1'] = team_game['goals_1'] - team_game['opp_goals_1'];
            team_game['goals_diff_2'] = team_game['goals_2'] - team_game['opp_goals_2'];
            team_game['goals_diff_3'] = team_game['goals_3'] - team_game['opp_goals_3'];
            // calculating points percentage
            if (team_game['games_played']) {
                team_game['pt_pctg'] = team_game['points'] / (team_game['games_played'] * 3.) * 100;
                team_game['pts_per_game'] = team_game['points'] / team_game['games_played'];
                team_game['goals_per_game'] = team_game['score'] / team_game['games_played'];
                team_game['opp_goals_per_game'] = team_game['opp_score'] / team_game['games_played'];
            } else {
                team_game['pt_pctg'] = 0;
                team_game['pts_per_game'] = 0;
                team_game['goals_per_game'] = 0;
                team_game['opp_goals_per_game'] = 0;
            }
            // calculating shot zone percentages
            if (team_game['shots']) {
                team_game['sl_p'] = parseFloat(((team_game['sl_sh'] / team_game['shots']) * 100).toFixed(2));
                team_game['lf_p'] = parseFloat(((team_game['lf_sh'] / team_game['shots']) * 100).toFixed(2));
                team_game['rg_p'] = parseFloat(((team_game['rg_sh'] / team_game['shots']) * 100).toFixed(2));
                team_game['bl_p'] = parseFloat(((team_game['bl_sh'] / team_game['shots']) * 100).toFixed(2));
            } else {
                team_game['sl_p'] = parseFloat((0).toFixed(2));
                team_game['lf_p'] = parseFloat((0).toFixed(2));
                team_game['rg_p'] = parseFloat((0).toFixed(2));
                team_game['bl_p'] = parseFloat((0).toFixed(2));
            }
            // calculating zone percentages for shots against
            if (team_game['opp_shots']) {
                team_game['sl_p_a'] = parseFloat(((team_game['sl_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
                team_game['lf_p_a'] = parseFloat(((team_game['lf_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
                team_game['rg_p_a'] = parseFloat(((team_game['rg_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
                team_game['bl_p_a'] = parseFloat(((team_game['bl_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
            } else {
                team_game['sl_p_a'] = parseFloat((0).toFixed(2));
                team_game['lf_p_a'] = parseFloat((0).toFixed(2));
                team_game['rg_p_a'] = parseFloat((0).toFixed(2));
                team_game['bl_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating shooting, save and zone percentages for shots on goal
            if (team_game['shots_on_goal']) {
                team_game['shot_pctg'] = parseFloat(((team_game['goals'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['opp_save_pctg'] = parseFloat(((team_game['opp_saves'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['sl_og_p'] = parseFloat(((team_game['sl_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['lf_og_p'] = parseFloat(((team_game['lf_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['rg_og_p'] = parseFloat(((team_game['rg_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['bl_og_p'] = parseFloat(((team_game['bl_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
            } else {
                team_game['shot_pct'] = parseFloat((0).toFixed(2));
                team_game['opp_save_pct'] = parseFloat((0).toFixed(2));
                team_game['sl_og_p'] = parseFloat((0).toFixed(2));
                team_game['lf_og_p'] = parseFloat((0).toFixed(2));
                team_game['rg_og_p'] = parseFloat((0).toFixed(2));
                team_game['bl_og_p'] = parseFloat((0).toFixed(2));
            }
            // calculating opponent shooting, save and zone percentages for shots on goal against
            if (team_game['opp_shots_on_goal']) {
                team_game['opp_shot_pctg'] = parseFloat(((team_game['opp_goals'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['save_pctg'] = parseFloat(((team_game['saves'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['sl_og_p_a'] = parseFloat(((team_game['sl_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['lf_og_p_a'] = parseFloat(((team_game['lf_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['rg_og_p_a'] = parseFloat(((team_game['rg_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['bl_og_p_a'] = parseFloat(((team_game['bl_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                team_game['opp_shot_pct'] = parseFloat((0).toFixed(2));
                team_game['save_pct'] = parseFloat((0).toFixed(2));
                team_game['sl_og_p_a'] = parseFloat((0).toFixed(2));
                team_game['lf_og_p_a'] = parseFloat((0).toFixed(2));
                team_game['rg_og_p_a'] = parseFloat((0).toFixed(2));
                team_game['bl_og_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating PDO
            team_game['pdo'] = parseFloat((parseFloat(team_game['shot_pctg']) + parseFloat(team_game['save_pctg'])).toFixed(2));
            team_game['opp_pdo'] = parseFloat((parseFloat(team_game['opp_shot_pctg']) + parseFloat(team_game['opp_save_pctg'])).toFixed(2));
            // calculating shots on goal for percentage
            if (team_game['shots_on_goal'] + team_game['opp_shots_on_goal']) {
                team_game['shot_for_pctg'] = parseFloat((team_game['shots_on_goal'] / (team_game['shots_on_goal'] + team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['opp_shot_for_pctg'] = parseFloat((team_game['opp_shots_on_goal'] / (team_game['shots_on_goal'] + team_game['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                team_game['shot_for_pctg'] = parseFloat((0).toFixed(2));
                team_game['opp_shot_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating unblocked shots (i.e. Fenwick) for percentage
            team_game['fenwick_events'] = team_game['shots_on_goal'] + team_game['shots_missed']; 
            team_game['opp_fenwick_events'] = team_game['opp_shots_on_goal'] + team_game['opp_shots_missed']; 
            if (team_game['fenwick_events'] + team_game['opp_fenwick_events']) {
                team_game['fenwick_for_pctg'] = parseFloat(((team_game['fenwick_events']) / (team_game['fenwick_events' ]+ team_game['opp_fenwick_events']) * 100).toFixed(2));
                team_game['opp_fenwick_for_pctg'] = parseFloat(((team_game['opp_fenwick_events']) / (team_game['fenwick_events' ]+ team_game['opp_fenwick_events']) * 100).toFixed(2));
            } else {
                team_game['fenwick_for_pctg'] = parseFloat((0).toFixed(2));
                team_game['opp_fenwick_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating shots (i.e. Corsi) for percentage
            if (team_game['shots'] + team_game['opp_shots']) {
                team_game['corsi_for_pctg'] = parseFloat((team_game['shots'] / (team_game['shots'] + team_game['opp_shots']) * 100).toFixed(2));
                team_game['opp_corsi_for_pctg'] = parseFloat((team_game['opp_shots'] / (team_game['shots'] + team_game['opp_shots']) * 100).toFixed(2));
            } else {
                team_game['corsi_for_pctg'] = parseFloat((0).toFixed(2));
                team_game['opp_corsi_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating power play percentage
            if (team_game['pp_opps']) {
                team_game['pp_pctg'] = parseFloat(((team_game['pp_goals'] / team_game['pp_opps']) * 100).toFixed(2));
            } else {
                team_game['pp_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating penalty killing percentage
            if (team_game['sh_opps']) {
                team_game['pk_pctg'] = parseFloat((100 - (team_game['opp_pp_goals'] / team_game['sh_opps']) * 100).toFixed(2));
            } else {
                team_game['pk_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating powerplay/penalty killing times per game
            if (team_game['games_played']) {
                team_game['pp_time_per_game'] = parseFloat((team_game['pp_time'] / team_game['games_played']).toFixed(2));
                team_game['pk_time_per_game'] = parseFloat((team_game['opp_pp_time'] / team_game['games_played']).toFixed(2));
            } else {
                team_game['pp_time_per_game'] = parseFloat((0).toFixed(2));
                team_game['pk_time_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating powerplay time per powerplay goal
            if (team_game['pp_goals']) {
                team_game['pp_time_per_pp_goal'] = parseFloat((team_game['pp_time'] / team_game['pp_goals']).toFixed(2));
            } else {
                team_game['pp_time_per_pp_goal'] = parseFloat((0).toFixed(2));
            }
            // calculating penalty killing time per opponent powerplay goal
            if (team_game['opp_pp_goals']) {
                team_game['pk_time_per_opp_pp_goal'] = parseFloat((team_game['opp_pp_time'] / team_game['opp_pp_goals']).toFixed(2));
            } else {
                team_game['pk_time_per_opp_pp_goal'] = parseFloat((0).toFixed(2));
            }
            // calculating special teams goal differential and combined special team percentages
            team_game['pp_pk_gdiff'] = team_game['pp_goals'] + team_game['sh_goals'] - team_game['opp_pp_goals'] - team_game['opp_sh_goals'];
            team_game['pp_pk_comb_pctg'] = team_game['pp_pctg'] + team_game['pk_pctg'];
            // calculating team faceoff percentage
            if (team_game['faceoffs']) {
                team_game['faceoff_pctg'] = parseFloat(((team_game['faceoffs_won'] / team_game['faceoffs']) * 100).toFixed(2));
            } else {
                team_game['faceoff_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating team penalty minutes per game
            if (team_game['games_played']) {
                team_game['pim_per_game'] = parseFloat((team_game['pim'] / team_game['games_played']).toFixed(2));
            } else {
                team_game['pim_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating average attendance per game
            if (home_road_type == 'home' && team_game['games_played']) {
                team_game['avg_attendance'] = parseFloat((team_game['attendance'] / team_game['games_played']).toFixed(0));
                // console.log(team_game['team'], home_road_type, team_game['avg_attendance'], team_game['capacity']);
            } else {
                team_game['avg_attendance'] = parseFloat((0).toFixed(2));
            }
            // calculating utilized capacity
            if (home_road_type == 'home' && team_game['games_played']) {
                team_game['util_capacity'] = parseFloat(((team_game['attendance'] / team_game['capacity']) * 100).toFixed(2));
                // console.log(home_road_type, team_game['util_capacity']);
            } else {
                team_game['util_capacity'] = parseFloat((0).toFixed(2));
            }
        });

        return full_team_stats;
    };

    $scope.scrollTo = function(id, to = 0) {
        // alert(id);
        var old = $location.hash();
        $timeout(function() {
            $location.hash(id);
            $anchorScroll();
        }, to);
        $location.hash(old);
    };

    if ($routeParams.anchor)
        $scope.scrollTo($routeParams.anchor, 500);

    // displaying only players with at least 10 faceoffs per game
    $scope.faceoffFilter = function(a) {
        if (!a['games_played']) {
            return false;
        };
        if (a['faceoffs'] / a['games_played'] < 10) {
            return false;
        };
        return true;
    };

    $scope.goalieMinutesPlayedFilter = function(a) {
        if (!a['toi']) {
            return false;
        };
        if (a['toi'] < ($scope.goalie_games_at_least_played * 3600)) {
            return false;
        };
        return true;
    };


    $scope.minPowerPlayPointsFilter = function(a) {
        if (!a['pp_points']) {
            return false;
        };
        if (a['pp_points'] < 1) {
            return false;
        };
        return true;
    };

    $scope.minShorthandedPointsFilter = function(a) {
        if (!a['sh_points']) {
            return false;
        };
        if (a['sh_points'] < 1) {
            return false;
        };
        return true;
    };

    $scope.filterPlayoffSeries = function(all_po_series) {
        if (all_po_series === undefined)
            return all_po_series;
        return $scope.po_series[$scope.current_game.home.shortcut].filter(series => series.opp_team === $scope.current_game.guest.shortcut);
    }

    $scope.changeDisplay = function() {
        if ($scope.league_display == 'active') {
            $scope.league_display = '';
        } else {
            $scope.league_display = 'active';
        }
        if ($scope.regional_display == 'active') {
            $scope.regional_display = '';
        } else {
            $scope.regional_display = 'active';
        }
    }

    $scope.toggleRosterDisplay = function() {
        if ($scope.roster_stats_display_item == 'current') {
            $scope.roster_stats_display_item = 'previous';
        } else if ($scope.roster_stats_display_item == 'previous') {
            $scope.roster_stats_display_item = 'career_against';
        } else {
            $scope.roster_stats_display_item = 'current';
        }
        console.log($scope.roster_stats_display_item);
    }

});
