(function () {

    window.socket = io.connect(window.location.protocol + '//' + document.domain + ':' + location.port + '/socket.io/');

    // individual game model definition
    var Game = Backbone.Model.extend({

        urlRoot: 'game',

        initialize: function () {

            var self = this;

            socket.on('update-game', function(game) { self.set(game) });
        }


    });

    var Games = Backbone.Collection.extend({

        model: Game

    });

    var OpenGames = Games.extend({

        url: 'open-games'

    });

    var openGames = new OpenGames();
    openGames.fetch();
    //console.log(openGames);

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
                    var template = _.template('<div class="end-stats"><h2><span class="friendable" data-user-id="<%= stats.winner_id %>"><%= stats.winner_username %></span> won <%= stats.winnings %> DYF!</h2><p>Begging playbacks: <%= stats.track.playbacks %><br>Ending playbacks: <%= stats.track.ending_playbacks %></p></div>');
                } else if ($('.game.parimutuel-dice').length) {
                    var template = _.template('<div class="end-stats"><h2>A dice roll of <%= stats.result %></h2></div>');
                }
                $('.stats').append(template(message));
            }

            // hide any matching game listing elements
            $('.game-listing[data-game-id='+message.id+']').hide();

            if (message.stats.winners.length) {
                self.modal(
                    message.stats.winners[0].username + " won " + message.stats.winners[0].winnings + " DYF!", 'h5', 'Round complete'
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

$(document).ready(function () { dyffy.init() });