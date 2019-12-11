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

    // starting to watch filter selection lists
    $scope.$watchGroup([
        'situationSelect', 'homeAwaySelect', 'seasonTypeSelect',
        'fromRoundSelect', 'toRoundSelect', 'weekdaySelect'
    ], function () {
        if ($scope.player_games) {
            $scope.filtered_player_stats = $scope.filterStats($scope.player_games);
        }
    }, true);

    // loading stats from external json file
    $http.get('data/' + $scope.season + '/del_player_game_stats_aggregated.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.stats = res.data[1];
    });

    // loading all players from external json file
    $http.get('data/del_players.json').then(function (res) {
        $scope.all_players = res.data;
    });

	$scope.readCSV = function() {
		// http get request to read CSV file content
        $http.get('/data/' + $scope.season + '/del_player_game_stats.csv').then($scope.processData);
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

    $scope.filterStats = function(stats) {
        filtered_player_stats = {};
        if ($scope.player_games === undefined)
            return filtered_player_stats;
        $scope.player_games.forEach(element => {
            plr_id = element['player_id'];
            if (!filtered_player_stats[plr_id]) {
                filtered_player_stats[plr_id] = {};
                filtered_player_stats[plr_id]['first_name'] = element['first_name'];
                filtered_player_stats[plr_id]['last_name'] = element['last_name'];
                filtered_player_stats[plr_id]['full_name'] = element['first_name'] + ' ' + element['last_name'];
                filtered_player_stats[plr_id]['age'] = $scope.all_players[plr_id]['age'];
                filtered_player_stats[plr_id]['u23'] = element['u23'];
                filtered_player_stats[plr_id]['iso_country'] = $scope.all_players[plr_id]['iso_country'];
                filtered_player_stats[plr_id]['position'] = $scope.all_players[plr_id]['position'];
                filtered_player_stats[plr_id]['teams'] = new Set();
                $scope.svc.player_stats_to_aggregate().forEach(category => {
                    filtered_player_stats[plr_id][category] = 0;
                });
            }
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

            if ($scope.fromDate) {
                if (date_to_test >= $scope.fromDate.startOf('day'))
                    is_equal_past_from_date = true;
            } else {
                is_equal_past_from_date = true;
            }
            if ($scope.toDate) {
                if (date_to_test <= $scope.toDate.startOf('day'))
                    is_prior_equal_to_date = true;
            } else {
                is_prior_equal_to_date = true;
            }
            if ($scope.homeAwaySelect) {
                if ($scope.homeAwaySelect === element.home_road)
                    is_selected_home_away_type = true;
            } else {
                is_selected_home_away_type = true;
            }
            if ($scope.situationSelect) {
                if (element[$scope.situationSelect])
                    is_selected_game_situation = true;
            } else {
                is_selected_game_situation = true;
            }
            if ($scope.seasonTypeSelect) {
                if ($scope.seasonTypeSelect === element.season_type)
                    is_selected_season_type = true;
            } else {
                is_selected_season_type = true;
            }
            if ($scope.weekdaySelect) {
                if ($scope.weekdaySelect == element.weekday)
                    is_selected_weekday = true;
            } else {
                is_selected_weekday = true;
            }
            if ($scope.fromRoundSelect) {
                if (element.round >= parseFloat($scope.fromRoundSelect))
                    is_equal_past_from_round = true;
            } else {
                is_equal_past_from_round = true;
            }
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
                $scope.svc.player_stats_to_aggregate().forEach(category => {
                    filtered_player_stats[plr_id][category] += element[category];
                });
                filtered_player_stats[plr_id]['teams'].add(element['team']);
            }
        });
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
            if (element['teams'].size == 1) {
                element['team'] = element['teams'].values().next().value;
            } else {
                element['team'] = element['teams'].size + ' Teams';
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
            // calculating goals, assists, points, shots, shots on goal per game
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
        // console.log(filtered_player_stats);
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

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/player_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // default filter values
    $scope.nameFilter = ''; // empty name filter
    $scope.teamFilter = ''; // empty name filter

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
    };

    $scope.changeDate = function() {
        if ($scope.player_games) {
            $scope.filtered_player_stats = $scope.filterStats($scope.player_games);
        };
    }

});