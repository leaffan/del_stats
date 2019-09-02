var app = angular.module('delStatsApp', ['ngResource', 'ngRoute', 'ngStorage', 'moment-picker', 'angularMoment'])

// main application configuration

app.config(['$routeProvider', function($routeProvider){
    $routeProvider
        .when('/home', {
            templateUrl: 'home.html',
        })
        .when('/del_stats', {
            title: 'Spielerstatistiken',
            templateUrl: 'player_stats.html',
            controller: 'plrStatsController as ctrl'
        })
        .when('/team_stats', {
            title: 'Teamstatistiken',
            templateUrl: 'team_stats.html',
            controller: 'teamStatsController as ctrl'
        })
        .when('/player_profile/:team/:player_id',
        {
            title: 'Spielerprofil',
            templateUrl: 'player_profile.html',
            controller: 'plrProfileController as ctrl'
        })
        .when('/team_profile/:team',
        {
            title: 'Teamprofil',
            templateUrl: 'team_profile.html',
            controller: 'teamProfileController as ctrl'
        })
        .otherwise({
            redirectTo: '/home'
        })
}]);

app.config(['momentPickerProvider', function(momentPickerProvider){
    momentPickerProvider.options({
        locale: 'de',
        format: 'L',
        minView: 'decade',
        maxView: 'day',
        startView: 'month',
        autoclose: true,
        keyboard: true
    })
}]);

app.run(['$rootScope', function($rootScope) {
    $rootScope.$on('$routeChangeSuccess', function (event, current, previous) {
        $rootScope.title = current.$$route.title;
    });
}]);

// providing functions to several controllers as services
app.factory('svc', function() {
    return {
        // sets sorting order according to selected sort criterion
        setSortOrder: function(sortCriterion, oldSortCriterion, oldStatsSortDescending, ascendingAttrs) {
            // if current criterion equals the new one
            if (oldSortCriterion === sortCriterion) {
                // just change sort direction
                return !oldStatsSortDescending;
            } else {
                // ascending for a few columns
                if (ascendingAttrs.indexOf(sortCriterion) !== -1) {
                    return false;
                } else {
                    // otherwise descending sort order
                    return true;
                }
            }
        },
        setSortOrder2: function(sortKey, oldSortConfig, globalSortConfig, ascendingAttrs) {
            // if previous sort key equals the new one
            if (oldSortConfig['sortKey'] == sortKey) {
                // just change sort direction
                return {
                    'sortKey': oldSortConfig['sortKey'],
                    'sortCriteria': oldSortConfig['sortCriteria'],
                    'sortDescending': !oldSortConfig['sortDescending']
                }
            } else {
                // ascending sort order for a few columns
                if (ascendingAttrs.indexOf(sortKey) !== -1) {
                    sortCriteria = globalSortConfig[sortKey] || sortKey;
                    return {
                        'sortKey': sortKey,
                        'sortCriteria': sortCriteria,
                        'sortDescending': false
                    }
                } else {
                    // otherwise descending sort order
                    sortCriteria = globalSortConfig[sortKey] || sortKey;
                    return {
                        'sortKey': sortKey,
                        'sortCriteria': sortCriteria,
                        'sortDescending': true
                    }
                }
            }
        },
        // formats time (in seconds) as mm:ss
        formatTime: function(timeInSeconds) {
            return Math.floor(timeInSeconds / 60) + ":" + ('00' + (Math.floor(timeInSeconds) % 60)).slice(-2);
        },
        // gets total sum of filtered attribute values
        getFilteredTotal: function(list, attribute, dataSource) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            for(var i = 0; i < list.length; i++){
                total += list[i][attribute];
            }
            return total;
        },
        // gets total sum of filtered attributed values through a specified game date
        getFilteredAccumulatedTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            for (var i = list.length-1; i >= 0; i--) {
                total += list[i][attribute];
                if (list[i]['game_date'] == to)
                {
                    return total;
                }
            }
            return total;
        },
        // gets average of filtered attributed values through a specified game date
        getFilteredAverageTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return;
            }
            var total = 0;
            var cnt_data = 0;
            for (var i = list.length-1; i >= 0; i--) {
                cnt_data++;
                total += list[i][attribute];
                
                if (list[i]['game_date'] == to)
                {
                    return total / cnt_data;
                }
            }
            return total / cnt_data;
        },
        parseFloat: function(floatAsString) {
            return parseFloat(floatAsString);
        },
        setTextColor: function(score, opp_score) {
            if (score > opp_score) {
                return " green";
            }
            else if (opp_score > score) {
                return " red";
            }
            else {
                return "";
            }
        }
    }
});
