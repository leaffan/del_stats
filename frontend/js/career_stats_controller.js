app.controller('careerStatsController', function ($scope, $http, $routeParams, svc) {

    $scope.svc = svc;
    $scope.table_select = 'career_stats_skaters';
    $scope.sortConfig = {
        'sortKey': 'pts',
        'sortCriteria': ['pts', 'ptspg', 'g', '-gp'],
        'sortDescending': true
    }

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/career_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // loading stats from external json file
    $http.get('data/career_stats/career_stats.json').then(function (res) {
        $scope.player_stats = res.data;
        $scope.full_player_stats = [];
        $scope.player_stats.forEach(element => {
            if (element['career']['all']) {
                c_stats = element['career']['all'];
                c_stats['player_id'] = element['player_id']
                c_stats['full_name'] = element['full_name']
                c_stats['position'] = element['position']
                $scope.full_player_stats.push(c_stats);
            }
        });

    });

    $scope.hasCareerFilter = function(a) {
        if (!a['career']['all']) {
            return false;
        }
        return true;
    };

    $scope.sort_def = {
        "pts": ['pts', 'ptspg', 'g', '-gp']
    };

    $scope.setSortOrder2 =  function(sortKey, oldSortConfig) {
        ascendingAttrs = ['full_name'];
        // if previous sort key equals the new one
        if (oldSortConfig['sortKey'] == sortKey) {
            // just change sort direction
            return {
                'sortKey': oldSortConfig['sortKey'],
                'sortCriteria': oldSortConfig['sortCriteria'],
                'sortDescending': !oldSortConfig['sortDescending']
            }
        } else {
            // ascending for a few columns
            if (ascendingAttrs.indexOf(sortKey) !== -1) {
                sortCriteria = $scope.sort_def[sortKey] || sortKey;
                return {
                    'sortKey': sortKey,
                    'sortCriteria': sortCriteria,
                    'sortDescending': false
                }
            } else {
                // otherwise descending sort order
                sortCriteria = $scope.sort_def[sortKey] || sortKey;
                return {
                    'sortKey': sortKey,
                    'sortCriteria': sortCriteria,
                    'sortDescending': true
                }
            }
        }
    }

});
