(function () {

    Dyffy = new Backbone.Marionette.Application();
    
    window.socket = io.connect(window.location.protocol + '//' + document.domain + ':' + location.port + '/socket.io/');

    Dyffy.on('start', function(options) {

        this.openGames = new OpenGames;
        this.myGames = new MyGames;
        this.recentGames = new RecentGames;
        this.friends = new Friends;
        this.others = new Others;
        this.wallet = new Wallet;

        this.addRegions({
            main: '#main',
            sidebar: '#sidebar'
        });

        // the router is responsible for directing control based on url
        this.router = Backbone.Marionette.AppRouter.extend({

            routes: {
                '': 'home'
            },

            home: function() { 

                new GamesView({

                    el: '.recent-games ul',

                    template: "#recent-games-template",

                    collection: Dyffy.recentGames,

                    collectionEvents: {
                        'reset': 'render'
                    }
                });

                new GamesView({

                    el: '.open-games ul',

                    collection: Dyffy.openGames,

                    collectionEvents: {
                        'reset': 'render'
                    }
                });

                new GamesView({

                    el: '.my-games ul',

                    collection: Dyffy.myGames,

                    collectionEvents: {
                        'reset': 'render'
                    }
                });

                new WalletView({

                    collection: Dyffy.wallet,

                    collectionEvents: {
                        'reset': 'render'
                    }
                });

                Dyffy.recentGames.fetch();
                Dyffy.openGames.fetch();
                Dyffy.myGames.fetch();
                Dyffy.friends.fetch();
                Dyffy.others.fetch();
                Dyffy.wallet.fetch();
            }
        });

        new this.router;

        Backbone.history.start();

    });

    // balance model
    var Balance = Backbone.Model.extend({

        initialize: function() {
            this.ioBind('update', this.update, this);
        },

        update: function(data) {
            this.set(data);
        },

        urlRoot: 'balance',
    });

    // wallet collection
    var Wallet = Backbone.Collection.extend({

        model: Balance,
        url: 'wallet',

        initialize: function() {
            this.ioBind('update', this.update, this);
        },

        update: function(data) {
            this.reset(data);
            console.log(this.length);
        }
    });

    // user model
    var User = Backbone.Model.extend({

        urlRoot: 'user',

        initialize: function() {
            this.ioBind('update', this.update, this);
        },

        update: function(data) {
            this.set(data);
        }
    });

    // friends collection
    var Friends = Backbone.Collection.extend({

        model: User,
        url: 'friends',

        initialize: function() {
            this.ioBind('update', this.update, this);
        },

        update: function(data) {
            this.reset(data);
        }
    });

    // others collection
    var Others = Backbone.Collection.extend({

        model: User,
        url: 'others',

        initialize: function() {
            this.ioBind('update', this.update, this);
        },

        update: function(data) {
            this.reset(data);
        }
    });

    // individual game model definition
    var Game = Backbone.Model.extend({

        initialize: function() {
 
            this.ioBind('update', this.update, this);
        },

        update: function(data) {

            this.set(data);
        },

        urlRoot: 'game',
    });

    // generic game collection
    var Games = Backbone.Collection.extend({

        model: Game,

        initialize: function() {
            this.ioBind('update', this.update, this);
        },

        update: function(data) {

            this.reset(data);
            console.log(this.length);
        }
    });

    // specific game collections
    var OpenGames = Games.extend({ 'url': 'open-games' });
    var MyGames = Games.extend({ 'url': 'my-games' });
    var RecentGames = Games.extend({ 'url': 'recent-games' });


    // views
    var WalletView = Backbone.Marionette.ItemView.extend({

        el: '.wallet ul',
        template: "#wallet-template"
    });

    var GamesView = Backbone.Marionette.ItemView.extend({

        template: "#games-template",
    });

    var FriendsView = Backbone.Marionette.CollectionView.extend({

        el: '.friends',
        template: "#friends-template"
    });

    var OthersView = Backbone.Marionette.CollectionView.extend({

        el: '.others',
        template: "#others-template"
    });

    //var ChatView = Backbone.Marionette.ItemView.extend({
    //    template: "#chat-template"
    //});

    var SidebarLayout = Marionette.LayoutView.extend({

        regions: {
            friends: '.friends',
            others: '.others',
            chat: '.chat',
            myGames: '.my-games',
            recentGames: '.recent-games',
            openGames: '.open-games',
            wallet: '.wallet'
        }    
    });

    var HomeLayout = Marionette.LayoutView.extend({

        regions: {
            recentGames: '.recent-games',
            openGames: '.open-games'
        }    
    });

    $(document).ready(function () { Dyffy.start() });

}());



var dyffy = {

    repeat: 100000,   // data synchronization interval

    init: function() {

        var self = this;

        this.smalltalk();

        // set game timer if we've detected one
        if (typeof game_end_time != 'undefined') {
        	this.setGameTimer(game_current_time, game_end_time);
        }

        // get game id if we;re on a game page
        this.game_id = $('.game[data-game-id]').attr('data-game-id');

        // populate chats
        socket.emit('get-chats');

    	// get and render friend lists
        var request_template = _.template('<li class="request"><% if (u.avatar) { %><img class="avatar" src="<%= u.avatar %>" /><% } else { %><i class="fa fa-user"></i><% }; %><span><%= u.username %></span><div class="status"><a class="accept" data-user-id="<%= u.id %>"><i class="fa fa-check-square"></i></a><a class="reject" data-user-id="<%= u.id %>"><i class="fa fa-minus-square"></i></a></div></li>');
		var pending_template = _.template('<li class="pending"><% if (u.avatar) { %><img class="avatar" src="<%= u.avatar %>" /><% } else { %><i class="fa fa-user"></i><% }; %><span><%= u.username %></span><div class="status">pending</div></li>');
		var friend_template = _.template('<li><% if (u.avatar) { %><img class="avatar" src="<%= u.avatar %>" /><% } else { %><i class="fa fa-user"></i><% }; %><span><%= u.username %></span></li>');
		var others_template = _.template('<li><% if (u.avatar) { %><img class="avatar" src="<%= u.avatar %>" /><% } else { %><i class="fa fa-user"></i><% }; %><span class="friendable"><%= u.username %></span></li>');
        
        socket.on('friend-list', function (message) {

            if (message['friends']) {

            	var e = $('#friends ul');
            	e.empty();
            	$(message.friends.request).each(function(i, f) {
            		e.append(request_template({u: f}));
            	});
            	$(message.friends.pending).each(function(i, f) {
            		e.append(pending_template({u: f}));
            	});
            	$(message.friends.friends).each(function(i, f) {
            		e.append(friends_template({u: f}));
            	})
            }

            if (message['others']) {

            	var e = $('#others ul');
            	e.empty();
            	$(message['others']).each(function(i, f) {
            		e.append(others_template({u: f}));
            	})
            }

            self.smalltalk();
        });

        // test socket
        socket.on('test', function (message) {
            console.log('test');
        });

        // game over
        socket.on('game-over', function (message) {

            // if we're on this game's page
            if ($('.game[data-game-id='+message.id+']')) {
                $('.stats .time-remaining').hide();
                if ($('.game.soundcloud').length) {
                    var template = _.template('<div class="end-stats"><h2><span class="friendable" data-user-id="<%= data.winner_id %>"><%= data.winner_username %></span> won <%= data.winnings %> DYF!</h2><p>Begging playbacks: <%= data.track.playbacks %><br>Ending playbacks: <%= data.track.ending_playbacks %></p></div>');
                } else if ($('.game.parimutuel-dice').length) {
                    var template = _.template('<div class="end-stats"><h2>A dice roll of <%= data.result %></h2></div>');
                }
                $('.stats').append(template(message));
            }

            // hide any matching game listing elements
            $('.game-listing[data-game-id='+message.id+']').hide();

            if (message.data.winners.length) {
                self.modal(
                    message.data.winners[0].username + " won " + message.data.winners[0].winnings + " DYF!", 'h5', 'Round complete'
                );
            }
        });

        // start game
        socket.on('start-game', function (message) {

            // hide any open game listing elements
            $('.open-game[data-game-id='+message.id+']').hide();

        	$('.rules').hide();
        	$('.stats').show();

        	self.setGameTimer(message.current_time, message.end_time);
        });

        // chat
        socket.on('chat', function (message) {
            $.each(message.chat, function(i, c) {
            	var chat = $("<li/>").html('<b>'+c.author+'</b><i>'+c.timestamp+'</i>'+c.comment)
            	$('#chat-box ul').append(chat);
            });
        });

        // add bet
        socket.on('add-bet', function (message) {

        	if (message.game_id == parseInt($('div[data-game-id]').attr('data-game-id'))) {

                if ($('.game.soundcloud').length) {
	        	    var template = _.template('<tr><td><b class="friendable" data-user-id="<%= bet.user.id %>"><%= bet.user.username %></b></td><td class="bet-guess"><%= bet.guess %> more listens</td><td class="bet-amount"><%= bet.amount %> DYF</td></tr>');
	            } else if ($('.game.parimutuel-dice').length) {
                    var template = _.template('<tr><td><b class="friendable" data-user-id="<%= bet.user.id %>"><%= bet.user.username %></b></td><td class="bet-guess">A dice roll of <%= bet.guess %></td><td class="bet-amount"><%= bet.amount %> DYF</td></tr>');
                }
            	$('#current-bets table').append(template({'bet': message.bet}));
	        	$('#current-bets').css('display', 'block');
	        }
        });

        // no more bets
        socket.on('no-more-bets', function (message) {

            // if we're on this game's page
            if ($('.game[data-game-id='+message.game_id+']')) {
                $('.bet').css('display', 'none');
            }
        	
        });

        // update balances
        socket.on('balance', function (message) {
            $.each(message, function(k, v) {
            	$('#'+k+'-balance .amount').text(v);
            })
        });

        // chat
        $('form#broadcast').submit(function (event) {
            event.preventDefault();
            socket.emit('chat', {
                data: $('#broadcast_data').val()
            });
            $('#broadcast_data').val('');
        });

        // bet
        $('form#bet').submit(function (event) {
            event.preventDefault();
            self.bet(this);
        });
    },

    bet: function(form) {

        var guess = $(form).find('#guess').val();
        var amount = $(form).find('#amount').val();

        socket.emit('bet', {
            amount: amount,
            guess: guess,
            game_id: this.game_id
        });
    },

    setGameTimer: function(current_time, end_time) {

        var self = this;

		var seconds_left = (new Date(end_time) - new Date(current_time)) / 1000;

		if (seconds_left > 0) {

			var minutes = parseInt(seconds_left / 60);
			var seconds = parseInt(seconds_left % 60);
			if (seconds < 10) { seconds = '0'+seconds }
			if (minutes < 10) { minutes = '0'+minutes }

			var timer_start = minutes+':'+seconds;

            $(".digits").each(function () {

                $(this).empty().countdown({

                    image: "/static/img/digits.png",
                    format: "mm:ss",
                    startTime: timer_start,
                    timerEnd: function() { 
                        $('.stats .time-remaining').hide();
                        setTimeout(function () {
                            socket.emit("finish-game", {'game_id': self.game_id});
                        }, 1500);
                    } 
                });
            });
		}

        socket.emit('get-time-remaining', {'game_id': this.game_id});

    },

    smalltalk: function() {

        var self = this;

        $('.friendable').each(function(i , e) {

        	var a = $('<i/>').addClass('fa fa-plus-square-o add-friend');
        	$(e).append(a);
        	$(e).on('click', function(event) {
        		var user_id = $(e).attr('data-user-id');
        		socket.emit('friend-request', {'user_id': user_id});	
        	});

        });

        $('.status .accept').each(function(i , e) {
        	$(e).on('click', function(event) {
        		var user_id = $(e).attr('data-user-id');
        		socket.emit('friend-accept', {'user_id': user_id});
        	});
        });

        $('.status .reject').each(function(i , e) {
        	$(e).on('click', function(event) {
        		var user_id = $(e).attr('data-user-id');
        		socket.emit('friend-reject', {'user_id': user_id});
        	});
        });
    },

    modal: function(bodytext, bodytag, headertext) {

        var modal_body;

        if (headertext) {
            $('#modal-header').empty().text(headertext);
        }

        if (bodytext) {
            modal_body = (bodytag) ? $('<' + bodytag + ' />') : $('<p />');
            $('#modal-body').empty().append(
                modal_body.addClass('modal-error-text').text(bodytext)
            );
        }

        $('#modal-dynamic').foundation('reveal', 'open');
    }
};

//$(document).ready(function () { dyffy.init() });