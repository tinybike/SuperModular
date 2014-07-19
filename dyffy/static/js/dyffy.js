(function ($) {

    function Cab() {

    	return this;
    }

    // setup methods called as part of the page load.
    Cab.prototype.ignition = function () {

        if (typeof game_started != 'undefined') {
        	this.setGameTimer(game_started, game_current_time, game_duration);
        }

        socket.emit('get-chats');

        return this;
    };

    // incoming websocket signals
    Cab.prototype.intake = function () {

    	// friend lists
        var self = this;
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

        // sync game timer
        socket.on('sync-timer', function (message) {

            self.setGameTimer(message.start_time, message.current_time, message.duration);
        });

        // start game
        socket.on('start-game', function (message) {

        	$('.rules').css('display', 'none');
        	$('.stats').css('display', 'block');

        	self.setGameTimer(message.start_time, message.current_time, message.duration)
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

	        	var template = _.template('<tr><td><b class="friendable" data-user-id="<%= bet.user.id %>"><%= bet.user.username %></b></td><td class="bet-guess"><%= bet.guess %> more listens</td><td class="bet-amount"><%= bet.amount %> DYF</td></tr>');
	        	$('#current-bets table').append(template({'bet': message.bet}));
	        	$('#current-bets').css('display', 'block');
	        }
        });

        // no more bets
        socket.on('no-more-bets', function () {
        	$('.bet').css('display', 'none');
        });

        // update balances
        socket.on('balance', function (message) {
            $.each(message, function(k, v) {
            	$('#'+k+'-balance .amount').text(v);
            })
        });

        return this;
    };

    // outgoing websocket signals
    Cab.prototype.exhaust = function () {

        var self = this;

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

        return this;
    };

    Cab.prototype.bet = function(form) {

        var self = this;

        var guess = $(form).find('#guess').val();
        var game_id = $(form).find('#game-id').val();
        var amount = 10;

        if (!isNaN(guess)) {

                socket.emit('bet', {
                    amount: amount,
                    guess: guess,
                    game_id: game_id
                });

        } else {

            error_text = "You must enter a number!";
            self.modal(error_text, 'h5', 'Betting error');
        }
    };

    Cab.prototype.setGameTimer = function(start_time, current_time, duration) {

		var ms_elapsed = new Date(current_time) - new Date(start_time);

		var total_seconds_left = (duration * 60) - parseInt(ms_elapsed / 1000);

		if (total_seconds_left > 0) {

			var minutes = parseInt(total_seconds_left / 60);
			var seconds = total_seconds_left % 60;
			if (seconds == 0) { seconds = '00' }
			else if (seconds < 10) { seconds = '0'+seconds }
			if (minutes == 0) { miuntes = '00' }
			else if (minutes < 10) { minutes = '0'+minutes }

			var start_time = minutes+':'+seconds;

		} else {

		 	var start_time = "00:00";
		 }

        $(".digits").each(function () {

            $(this).empty().countdown({
                image: "static/img/digits.png",
                format: "mm:ss",
                startTime: start_time,
                timerEnd: function () { }
            });
        });
    };

    // interim function to encapsulate friending events 
    // TODO: backbone this shit
    Cab.prototype.smalltalk = function() {

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
    };

    $(document).ready(function () {

        var repeat = 30000;   // data synchronization interval

        window.socket = io.connect(window.location.protocol + '//' + document.domain + ':' + location.port + '/socket.io/');

        new Cab()
        	.ignition()
        	.intake()
        	.exhaust()
        	.smalltalk();

    });

})(jQuery);