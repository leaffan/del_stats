app.controller('plrStatsController', function ($scope, $http, $routeParams, svc) {

    $scope.svc = svc;
    $scope.season = $routeParams.season;
    // default table selection and sort criterion for skater page
    $scope.tableSelect = 'basic_stats';
    $scope.seasonTypeSelect = 'RS';
    $scope.scoringStreakTypeFilter = 'points';
    $scope.showStrictStreaks = true;
    $scope.u23Check = false;
    // setting default sort configuration
    $scope.sortConfig = {
        'sortKey': 'points',
        'sortCriteria': ['points', '-games_played', 'goals', 'primary_points'],
        'sortDescending': true
    }
    $scope.fromRoundSelect = '1';
    // default filter values
    $scope.nameFilter = ''; // empty name filter
    $scope.teamFilter = ''; // empty name filter

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/player_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // starting to watch filter selection lists
    $scope.$watchGroup([
        'homeAwaySelect', 'seasonTypeSelect',
        'fromRoundSelect', 'toRoundSelect', 'weekdaySelect'
    ], function () {
        if ($scope.player_games) {
            $scope.filtered_player_stats = $scope.filterStats($scope.player_games);
        }
        if ($scope.goalie_games) {
            $scope.filtered_goalie_stats = $scope.filterGoalieStats($scope.goalie_games);
        }
    }, true);

    // loading all players from external json file
    $http.get('data/del_players.json').then(function (res) {
        $scope.all_players = res.data;
    });

    // loading stats from external json file
    $http.get('data/' + $scope.season + '/del_player_game_stats_aggregated.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.stats = res.data[1];
    });

    // loading goalie stats from external json file
    $http.get('data/' + $scope.season + '/del_goalie_game_stats.json').then(function (res) {
        $scope.goalie_games = res.data;
        $scope.filtered_goalie_stats = $scope.filterGoalieStats($scope.goalie_games);
    });
    
	$scope.readCSV = function() {
		// http get request to read CSV file content
        $http.get('data/' + $scope.season + '/del_player_game_stats.csv').then($scope.processData);
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
        // retrieving maximum round played
        $scope.maxRoundPlayed = Math.max.apply(Math, $scope.player_games.map(function(o) { return o.round; })).toString();
        // retrieving all weekdays a game was played
        $scope.weekdaysPlayed = [...new Set($scope.player_games.map(item => item.weekday))].sort();
        // retrieving all months a game was played by the current team
        $scope.monthsPlayed = [...new Set($scope.player_games.map(item => moment(item.game_date).month()))];
        // setting to round selection to maximum round played
        $scope.toRoundSelect = $scope.maxRoundPlayed;
        $scope.filtered_player_stats = $scope.filterStats($scope.player_games);
	};

    $scope.readCSV();

    $scope.filterGoalieStats = function(stats) {
        filtered_goalie_stats = {};
        goalie_teams = {};
        if ($scope.goalie_games === undefined)
            return filtered_goalie_stats;
        $scope.goalie_games.forEach(element => {
            plr_id = element['goalie_id'];
            team = element['team'];
            key = [plr_id, team];
            if (!filtered_goalie_stats[key]) {
                filtered_goalie_stats[key] = {};
                filtered_goalie_stats[key]['player_id'] = plr_id;
                filtered_goalie_stats[key]['first_name'] = element['first_name'];
                filtered_goalie_stats[key]['last_name'] = element['last_name'];
                filtered_goalie_stats[key]['full_name'] = element['first_name'] + ' ' + element['last_name'];
                filtered_goalie_stats[key]['age'] = $scope.all_players[plr_id]['age'];
                filtered_goalie_stats[key]['u23'] = element['u23'];
                filtered_goalie_stats[key]['iso_country'] = $scope.all_players[plr_id]['iso_country'];
                filtered_goalie_stats[key]['position'] = $scope.all_players[plr_id]['position'];
                filtered_goalie_stats[key]['team'] = element['team'];
                filtered_goalie_stats[key]['single_team'] = true;
                $scope.svc.goalie_stats_to_aggregate().forEach(category => {
                    filtered_goalie_stats[key][category] = 0;
                });
            }
            // checking whether current element passes all filters
            if ($scope.elementPassedFilters(element))
            {
                // adding values
                $scope.svc.goalie_stats_to_aggregate().forEach(category => {
                    filtered_goalie_stats[key][category] += element[category];
                });
                // registering player's team
                if (!goalie_teams[plr_id]) {
                    goalie_teams[plr_id] = new Set();
                }
                goalie_teams[plr_id].add(team);
            }
        });

        $scope.processMultiTeamPlayers(filtered_goalie_stats, goalie_teams, true);
        filtered_goalie_stats = Object.values(filtered_goalie_stats);

        filtered_goalie_stats.forEach(element => {
            // calculating standard save percentage
            if (element['shots_against']) {
                element['save_pctg'] = (1 - element['goals_against'] / element['shots_against']) * 100.;
            } else {
                element['save_pctg'] = parseFloat(0);
            }
            if (element['toi']) {
                element['gaa'] = (element['goals_against'] * 3600.) / element['toi'];
            } else {
                element['gaa'] = parseFloat(0);
            }
            // calculating grouped save percentages in even strength
            if (element['sa_5v5']) {
                element['save_pctg_5v5'] = (1 - element['ga_5v5'] / element['sa_5v5']) * 100.;
            } else {
                element['save_pctg_5v5'] = null;
            }
            if (element['sa_4v4']) {
                element['save_pctg_4v4'] = (1 - element['ga_4v4'] / element['sa_4v4']) * 100.;
            } else {
                element['save_pctg_4v4'] = null;
            }
            if (element['sa_3v3']) {
                element['save_pctg_3v3'] = (1 - element['ga_3v3'] / element['sa_3v3']) * 100.;
            } else {
                element['save_pctg_3v3'] = null;
            }
            // calculating grouped shorthanded save percentages
            if (element['sa_4v5']) {
                element['save_pctg_4v5'] = (1 - element['ga_4v5'] / element['sa_4v5']) * 100.;
            } else {
                element['save_pctg_4v5'] = null;
            }
            if (element['sa_3v4']) {
                element['save_pctg_3v4'] = (1 - element['ga_3v4'] / element['sa_3v4']) * 100.;
            } else {
                element['save_pctg_3v4'] = null;
            }
            if (element['sa_3v5']) {
                element['save_pctg_3v5'] = (1 - element['ga_3v5'] / element['sa_3v5']) * 100.;
            } else {
                element['save_pctg_3v5'] = null;
            }
            // calculating grouped powerplay save percentages
            if (element['sa_5v4']) {
                element['save_pctg_5v4'] = (1 - element['ga_5v4'] / element['sa_5v4']) * 100.;
            } else {
                element['save_pctg_5v4'] = null;
            }
            if (element['sa_4v3']) {
                element['save_pctg_4v3'] = (1 - element['ga_4v3'] / element['sa_4v3']) * 100.;
            } else {
                element['save_pctg_4v3'] = null;
            }
            if (element['sa_5v3']) {
                element['save_pctg_5v3'] = (1 - element['ga_5v3'] / element['sa_5v3']) * 100.;
            } else {
                element['save_pctg_5v3'] = null;
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
            if (element['sa_neutral_zone']) {
                element['save_pctg_neutral_zone'] = (1 - element['ga_neutral_zone'] / element['sa_neutral_zone']) * 100.;
            } else {
                element['save_pctg_neutral_zone'] = null;
            }
        });

        return filtered_goalie_stats;
    }

    $scope.elementPassedFilters = function(element) {
        is_equal_past_from_date = false;
        is_prior_equal_to_date = false;
        is_selected_home_away_type = false;
        is_selected_game_situation = false;
        is_selected_season_type = false;
        is_selected_weekday = false;
        is_equal_past_from_round = false;
        is_prior_equal_to_round = false;

        // retrieving game date as moment structure
        date_to_test = moment(element.game_date);

        // testing selected from date
        if ($scope.fromDate) {
            if (date_to_test >= $scope.fromDate.startOf('day'))
                is_equal_past_from_date = true;
        } else {
            is_equal_past_from_date = true;
        }
        // testing selected to date
        if ($scope.toDate) {
            if (date_to_test <= $scope.toDate.startOf('day'))
                is_prior_equal_to_date = true;
        } else {
            is_prior_equal_to_date = true;
        }
        // testing home/away selection
        if ($scope.homeAwaySelect) {
            if ($scope.homeAwaySelect === element.home_road)
                is_selected_home_away_type = true;
        } else {
            is_selected_home_away_type = true;
        }
        // testing selected game situation
        if ($scope.situationSelect) {
            if (element[$scope.situationSelect])
                is_selected_game_situation = true;
        } else {
            is_selected_game_situation = true;
        }
        // testing selected season type
        if ($scope.seasonTypeSelect) {
            if ($scope.seasonTypeSelect === element.season_type)
                is_selected_season_type = true;
        } else {
            is_selected_season_type = true;
        }
        // testing selected weekday
        if ($scope.weekdaySelect) {
            if ($scope.weekdaySelect == element.weekday)
                is_selected_weekday = true;
        } else {
            is_selected_weekday = true;
        }
        // testing selected from round
        if ($scope.fromRoundSelect) {
            if (element.round >= parseFloat($scope.fromRoundSelect))
                is_equal_past_from_round = true;
        } else {
            is_equal_past_from_round = true;
        }
        // testing selected to round
        if ($scope.toRoundSelect) {
            if (element.round <= parseFloat($scope.toRoundSelect))
                is_prior_equal_to_round = true;
        } else {
            is_prior_equal_to_round = true;
        }

        // finally aggregating values of all season stat lines that have been filtered
        if (
            is_equal_past_from_date && is_prior_equal_to_date &&
            is_selected_home_away_type && is_selected_game_situation &&
            is_selected_season_type && is_selected_weekday &&
            is_equal_past_from_round && is_prior_equal_to_round
        ) {
            return true;
        } else {
            return false;
        }
    }

    $scope.processMultiTeamPlayers = function(filtered_stats, player_teams, goalies=false) {
        // identifying multi-team players
        var multiTeamPlayers = Object.keys(player_teams).reduce((p, plr_id) => {
            if (player_teams[plr_id].size > 1) p[plr_id] = player_teams[plr_id];
            return p;
        }, {});

        // combining single-team stats of players that have dressed for multiple teams 
        Object.keys(multiTeamPlayers).forEach(plr_id => {
            teams = multiTeamPlayers[plr_id];
            key = [plr_id, teams.size];
            multiTeamPlayerStats = {}
            if (goalies) {
                svc.goalie_stats_to_aggregate().forEach(category => {
                    multiTeamPlayerStats[category] = 0;
                });
            } else {
                svc.player_stats_to_aggregate().forEach(category => {
                    multiTeamPlayerStats[category] = 0;
                });
            }
            // aggregating numeric attributes
            teams.forEach(team => {
                plr_team_stats = filtered_stats[[plr_id, team]];
                if (goalies) {
                    svc.goalie_stats_to_aggregate().forEach(category => {
                        multiTeamPlayerStats[category] += plr_team_stats[category];
                    });
                } else {
                    svc.player_stats_to_aggregate().forEach(category => {
                        multiTeamPlayerStats[category] += plr_team_stats[category];
                    });
                }
            });
            // finally setting non-numeric attributes
            multiTeamPlayerStats['team'] = teams.size + " Tms";
            multiTeamPlayerStats['player_id'] = plr_id;
            multiTeamPlayerStats['first_name'] = plr_team_stats['first_name'];
            multiTeamPlayerStats['last_name'] = plr_team_stats['last_name'];
            multiTeamPlayerStats['full_name'] = plr_team_stats['first_name'] + ' ' + plr_team_stats['last_name'];
            multiTeamPlayerStats['age'] = plr_team_stats['age'];
            multiTeamPlayerStats['u23'] = plr_team_stats['u23'];
            multiTeamPlayerStats['iso_country'] = plr_team_stats['iso_country'];
            multiTeamPlayerStats['position'] = plr_team_stats['position'];
            // setting flag to make current dataset identifiable for multi-team content
            multiTeamPlayerStats['single_team'] = false;
            filtered_stats[[plr_id, teams]] = multiTeamPlayerStats;
        });
    }

    $scope.filterStats = function(stats) {
        filtered_player_stats = {};
        player_teams = {};
        if ($scope.player_games === undefined)
            return filtered_player_stats;
        $scope.player_games.forEach(element => {
            plr_id = element['player_id'];
            team = element['team'];
            key = [plr_id, team]
            if (!filtered_player_stats[key]) {
                filtered_player_stats[key] = {};
                filtered_player_stats[key]['player_id'] = plr_id;
                filtered_player_stats[key]['first_name'] = element['first_name'];
                filtered_player_stats[key]['last_name'] = element['last_name'];
                filtered_player_stats[key]['full_name'] = element['first_name'] + ' ' + element['last_name'];
                filtered_player_stats[key]['age'] = $scope.all_players[plr_id]['age'];
                filtered_player_stats[key]['u23'] = element['u23'];
                filtered_player_stats[key]['iso_country'] = $scope.all_players[plr_id]['iso_country'];
                filtered_player_stats[key]['position'] = $scope.all_players[plr_id]['position'];
                filtered_player_stats[key]['team'] = element['team'];
                filtered_player_stats[key]['single_team'] = true;
                $scope.svc.player_stats_to_aggregate().forEach(category => {
                    filtered_player_stats[key][category] = 0;
                });
            }
            // checking whether current element passes all filters
            if ($scope.elementPassedFilters(element))
            {
                // adding values
                $scope.svc.player_stats_to_aggregate().forEach(category => {
                    filtered_player_stats[key][category] += element[category];
                });
                // registering player's team
                if (!player_teams[plr_id]) {
                    player_teams[plr_id] = new Set();
                }
                player_teams[plr_id].add(team);
            }
        });

        $scope.processMultiTeamPlayers(filtered_player_stats, player_teams);
        // flattening filtered player stats
        filtered_player_stats = Object.values(filtered_player_stats);

        filtered_player_stats.forEach(element => {
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
            // calculating team faceoff percentage
            if (element['faceoffs']) {
                element['faceoff_pctg'] = parseFloat(((element['faceoffs_won'] / element['faceoffs']) * 100).toFixed(2));
            } else {
                element['faceoff_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating power play points per 60
            if (element['time_on_ice_pp']) {
                element['pp_goals_per_60'] = element['pp_goals'] / (element['time_on_ice_pp'] / 60) * 60;
                element['pp_assists_per_60'] = element['pp_assists'] / (element['time_on_ice_pp'] / 60) * 60;
                element['pp_points_per_60'] = element['pp_points'] / (element['time_on_ice_pp'] / 60) * 60;
            } else {
                element['pp_goals_per_60'] = parseFloat((0).toFixed(2));
                element['pp_assists_per_60'] = parseFloat((0).toFixed(2));
                element['pp_points_per_60'] = parseFloat((0).toFixed(2));
            }
            // calculating time on ice and shifts per game
            if (element['games_played']) {
                element['time_on_ice_per_game'] = (element['time_on_ice'] / element['games_played']).toFixed(2);
                element['time_on_ice_pp_per_game'] = (element['time_on_ice_pp'] / element['games_played']).toFixed(2);
                element['time_on_ice_sh_per_game'] = (element['time_on_ice_sh'] / element['games_played']).toFixed(2);
                element['shifts_per_game'] = element['shifts'] / element['games_played'];
            } else {
                element['time_on_ice_per_game'] = parseFloat((0).toFixed(2));
                element['time_on_ice_pp_per_game'] = parseFloat((0).toFixed(2));
                element['time_on_ice_sh_per_game'] = parseFloat((0).toFixed(2));
                element['shifts_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating goals, assists, points, shots, shots on goal per 60 minutes of time on ice
            if (element['time_on_ice']) {
                element['goals_per_60'] = element['goals'] / (element['time_on_ice'] / 60) * 60;
                element['assists_per_60'] = element['assists'] / (element['time_on_ice'] / 60) * 60;
                element['primary_assists_per_60'] = element['primary_assists'] / (element['time_on_ice'] / 60) * 60;
                element['secondary_assists_per_60'] = element['secondary_assists'] / (element['time_on_ice'] / 60) * 60;
                element['points_per_60'] = element['points'] / (element['time_on_ice'] / 60) * 60;
                element['primary_points_per_60'] = element['primary_points'] / (element['time_on_ice'] / 60) * 60;
                element['shots_per_60'] = element['shots'] / (element['time_on_ice'] / 60) * 60;
                element['shots_on_goal_per_60'] = element['shots_on_goal'] / (element['time_on_ice'] / 60) * 60;
            } else {
                element['goals_per_60'] = parseFloat((0).toFixed(2));
                element['assists_per_60'] = parseFloat((0).toFixed(2));
                element['primary_assists_per_60'] = parseFloat((0).toFixed(2));
                element['secondary_assists_per_60'] = parseFloat((0).toFixed(2));
                element['points_per_60'] = parseFloat((0).toFixed(2));
                element['primary_points_per_60'] = parseFloat((0).toFixed(2));
                element['shots_per_60'] = parseFloat((0).toFixed(2));
                element['shots_on_goal_per_60'] = parseFloat((0).toFixed(2));
            }
            // calculating goals, assists, points, shots, shots on goal per game
            if (element['games_played']) {
                element['goals_per_game'] = element['goals'] / element['games_played'];
                element['assists_per_game'] = element['assists'] / element['games_played'];
                element['primary_assists_per_game'] = element['primary_assists'] / element['games_played'];
                element['secondary_assists_per_game'] = element['secondary_assists'] / element['games_played'];
                element['points_per_game'] = element['points'] / element['games_played'];
                element['primary_points_per_game'] = element['primary_points'] / element['games_played'];
                element['shots_per_game'] = element['shots'] / element['games_played'];
                element['shots_on_goal_per_game'] = element['shots_on_goal'] / element['games_played'];
            } else {
                element['goals_per_game'] = parseFloat((0).toFixed(2));
                element['assists_per_game'] = parseFloat((0).toFixed(2));
                element['primary_assists_per_game'] = parseFloat((0).toFixed(2));
                element['secondary_assists_per_game'] = parseFloat((0).toFixed(2));
                element['points_per_game'] = parseFloat((0).toFixed(2));
                element['primary_points_per_game'] = parseFloat((0).toFixed(2));
                element['shots_per_game'] = parseFloat((0).toFixed(2));
                element['shots_on_goal_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating shot zone percentages
            if (element['shots']) {
                element['slot_pctg'] = (element['slot_shots'] / element['shots']) * 100.; 
                element['left_pctg'] = (element['left_shots'] / element['shots']) * 100.; 
                element['right_pctg'] = (element['right_shots'] / element['shots']) * 100.; 
                element['blue_line_pctg'] = (element['blue_line_shots'] / element['shots']) * 100.; 
                element['neutral_zone_pctg'] = (element['neutral_zone_shots'] / element['shots']) * 100.; 
            } else {
                element['slot_pctg'] = parseFloat((0).toFixed(2)); 
                element['left_pctg'] = parseFloat((0).toFixed(2)); 
                element['right_pctg'] = parseFloat((0).toFixed(2)); 
                element['blue_line_pctg'] = parseFloat((0).toFixed(2)); 
                element['neutral_zone_pctg'] = parseFloat((0).toFixed(2)); 
            }
            // calculating shot-on-goal zone percentages
            if (element['shots_on_goal']) {
                element['slot_on_goal_pctg'] = (element['slot_on_goal'] / element['shots_on_goal']) * 100.; 
                element['left_on_goal_pctg'] = (element['left_on_goal'] / element['shots_on_goal']) * 100.; 
                element['right_on_goal_pctg'] = (element['right_on_goal'] / element['shots_on_goal']) * 100.; 
                element['blue_line_on_goal_pctg'] = (element['blue_line_on_goal'] / element['shots_on_goal']) * 100.; 
                element['neutral_zone_on_goal_pctg'] = (element['neutral_zone_on_goal'] / element['shots_on_goal']) * 100.; 
            } else {
                element['slot_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
                element['left_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
                element['right_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
                element['blue_line_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
                element['neutral_zone_on_goal_pctg'] = parseFloat((0).toFixed(2)); 
            }
            // calculating time on ice per shift
            if (element['shifts']) {
                element['time_on_ice_per_shift'] = element['time_on_ice'] / element['shifts']
            } else {
                element['time_on_ice_per_shift'] = parseFloat((0).toFixed(2));
            }

        });
        return filtered_player_stats;
    };

    // loading strictly defined player scoring streaks from external json file
    $http.get('data/' + $scope.season + '/del_streaks_strict.json').then(function (res) {
        $scope.strict_streaks = res.data;
        $scope.streaks = $scope.strict_streaks;
    });
    // loading loosely defined player scoring streaks from external json file
    $http.get('data/' + $scope.season + '/del_streaks_loose.json').then(function (res) {
        $scope.loose_streaks = res.data;
    });

    // default sorting criteria for all defined tables
    $scope.tableSortCriteria = {
        'player_information': 'last_name',
        'streaks': 'length',
        'basic_stats': 'points',
        'on_goal_shot_zones': 'shots_on_goal',
        'shot_zones': 'shots',
        'per_game_stats': 'points_per_game',
        'time_on_ice_shift_stats': 'time_on_ice',
        'power_play_stats': 'time_on_ice_pp',
        'penalty_stats': 'pim_from_events',
        'additional_stats': 'faceoff_pctg',
        'on_ice_stats': 'plus_minus',
        'per_60_stats': 'points_per_60',
        'goalie_stats': 'save_pctg',
        'goalie_stats_ev': 'save_pctg_5v5',
        'goalie_stats_sh': 'save_pctg_4v5',
        'goalie_stats_pp': 'save_pctg_5v4',
        'goalie_zone_stats_near': 'save_pctg_slot',
        'goalie_zone_stats_far': 'save_pctg_blue_line'
    }

    // sorting attributes to be used in ascending order
    $scope.ascendingAttrs = [
        'last_name', 'team', 'position', 'shoots',
        'date_of_birth', 'iso_country', 'gaa', 'from_date', 'to_date'
    ];

    // actual sorting criteria for various sorting attributes, including
    // criteria for tie breaking
    $scope.sortCriteria = {
        "last_name": ['last_name', 'team'],
        "points": ['points', '-games_played', 'goals', 'primary_points'],
        "assists": ['assists', '-games_played', 'primary_assists'],
        "goals": ['goals', '-games_played', 'points'],
        "games_played": ['games_played', '-team'],
        "length": ['length', 'points', 'from_date'],
        "save_pctg_blue_line": ['save_pctg_blue_line', 'sa_blue_line'],
        'save_pctg_slot': ['save_pctg_slot', 'sa_slot'],
        'save_pctg_5v4': ['save_pctg_5v4', 'sa_5v4'],
        'save_pctg_4v5': ['save_pctg_4v5', 'sa_4v5'],
        'save_pctg_5v5': ['save_pctg_5v5', 'sa_5v5'],
        'save_pctg': ['save_pctg', 'shots_against', 'toi'],
        'points_per_60': ['points_per_60', 'time_on_ice_seconds'],
        'shots_on_goal': ['shots_on_goal', 'slot_on_goal_pctg', 'slot_on_goal'],
        'shots': ['shots', 'slot_pctg', 'slot_shots'],
        'points_per_game': ['points_per_game', 'primary_points_per_game'],
        'time_on_ice': ['time_on_ice', 'shifts'],
        'time_on_ice_pp': ['time_on_ice_pp', 'pp_goals_per_60'],
        'pim_from_events': ['pim_from_events', '-games_played'],
        'faceoff_pctg': ['faceoff_pctg', 'faceoffs'],
        'plus_minus': ['plus_minus']
    };

    // changing sorting criteria according to table selected for display
    $scope.changeTable = function() {
        sortKey = $scope.tableSortCriteria[$scope.tableSelect];
        if ($scope.ascendingAttrs.indexOf(sortKey) !== -1) {
            sortDescending = false;
        } else {
            sortDescending = true;
        }
        $scope.sortConfig = {
            'sortKey': sortKey,
            'sortCriteria': $scope.sortCriteria[sortKey],
            'sortDescending': sortDescending
        };
    };

    // function to change sort order, actually just a wrapper around a service
    // function defined above
    $scope.setSortOrder = function(sortKey, oldSortConfig) {
        return svc.setSortOrder2(sortKey, oldSortConfig, $scope.sortCriteria, $scope.ascendingAttrs);
    };

    // filter definitions
    $scope.greaterThanFilter = function (prop, val) {
        return function (item) {
            return item[prop] > val;
        }
    }

    $scope.u23Filter = function(a) {
        if (!$scope.u23Check)
            return true;
        if ($scope.u23Check && a.u23) {
            return true;
        } else {
            return false;
        }
    };

    $scope.longestStreakFilter = function(a) {
        if (!$scope.showOnlyLongestStreak) {
            return true;
        }
        if ($scope.showOnlyLongestStreak && a.longest) {
            return true;
        } else {
            return false;
        }
    };

    $scope.currentStreakFilter = function(a) {
        if (!$scope.showOnlyCurrentStreak)
            return true;
        if ($scope.showOnlyCurrentStreak && a.current) {
            return true;
        } else {
            return false;
        }
    };

    $scope.minimumAgeFilter = function (a) {
        if ($scope.minimumAge) {
            if (a.age < $scope.minimumAge) {
                return false;
            } else {
                return true;
            }
        } else {
            return true;
        }
    };

    $scope.maximumAgeFilter = function (a) {
        if ($scope.maximumAge) {
            if (a.age > $scope.maximumAge) {
                return false;
            } else {
                return true;
            }
        } else {
            return true;
        }
    };

    $scope.changeStreakType = function() {
        if ($scope.showStrictStreaks) {
            $scope.streaks = $scope.strict_streaks;
        } else {
            $scope.streaks = $scope.loose_streaks;
        }
    };

    $scope.changeTimespan = function() {
        if (!$scope.timespanSelect) {
            $scope.fromDate = null;
            $scope.toDate = null;
            return;
        }
        timespanSelect = parseInt($scope.timespanSelect) + 1;
        if (timespanSelect < 9) {
            season = parseInt($scope.season) + 1;
        } else {
            season = parseInt($scope.season);
        }
        $scope.fromDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D');
        $scope.toDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D').endOf('month');
        $scope.changeDate();
    };

    $scope.changeDate = function() {
        if ($scope.player_games) {
            $scope.filtered_player_stats = $scope.filterStats($scope.player_games);
        };
        if ($scope.goalie_games) {
            $scope.filtered_goalie_stats = $scope.filterGoalieStats($scope.goalie_games);
        }
    }

});