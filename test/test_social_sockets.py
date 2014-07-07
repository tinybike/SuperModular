from flask import session, request, escape
from dyffy.utils import *
from dyffy import app, db, socketio
from decimal import *
import unittest
from socket_test import SocketTest

class TestSocialSockets(SocketTest):
    """
    Social networking WebSocket tests
    """
    def setUp(self):
        SocketTest.setUp(self)
        self.profile_name = u'tinybike'
        delete_friends_query = (
            "DELETE FROM friends WHERE username1 = %s OR username2 = %s"
        )
        with db.cursor_context() as cur:
            cur.execute(delete_friends_query, (self.username,)*2)
        select_user_id_query = "SELECT user_id FROM users WHERE username = %s"
        select_friends = (
            "SELECT count(*) FROM friends "
            "WHERE username1 = %s OR username2 = %s"
        )
        with db.cursor_context() as cur:
            cur.execute(select_user_id_query, (self.profile_name,))
            self.assertEqual(cur.rowcount, 1)
            self.profile_id = cur.fetchone()[0]
            self.assertEqual(type(self.profile_id), long)
            cur.execute(select_friends, (self.username,)*2)
            self.assertEqual(cur.fetchone()[0], 0)
        self.tables = ('friends', 'friend_requests', 'award_tracking',
                       'scribble', 'chatbox')
        verify_award_tracking_setup()
        self.awards = []
        self.award_categories = ('friends', 'chat', 'trading', 'scribble')
        self.user_icon = 'placeholder'
        self.profile_icon = 'cyclicoin.png'
        # TODO delete these messages during teardown
        self.scribble_message = "Scribbling a scribbly scribble"
        self.chat_message = "Chatty chat chat"
        select_awards_query = (
            "SELECT award_id, number_of_winners FROM awards ORDER BY award_id"
        )
        self.initial_winners = {}
        with db.cursor_context(True) as cur:
            cur.execute(select_awards_query)
            for row in cur:
                self.initial_winners[row['award_id']] = \
                    row['number_of_winners']

    def test_awards_list(self):
        """WebSocket: /socket.io/get-awards-list"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'get-awards-list',
        })
        self.assertEqual(signal, 'awards-list')
        self.assertIn('awards', data)
        self.assertGreater(len(data['awards']), 6)
        fields = ('award_name', 'category', 'points',
                  'award_description', 'icon')
        for award in data['awards']:
            for field in fields:
                self.assertIn(field, award)
                if field == 'points':
                    self.assertEqual(type(award[field]), long)
                else:
                    self.assertEqual(type(award[field]), str)

    def test_friend_request(self):
        """WebSocket: /socket.io/friend-request"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'friend-request',
            'requester_name': self.profile_name,
            'requester_id': self.profile_id,
        })
        self.assertEqual(signal, 'friend-requested')
        self.assertIn('requestee', data)
        self.assertEqual(data['requestee'], self.profile_name)
        query = (
            "SELECT requester_id, requestee_name, requestee_id "
            "FROM friend_requests WHERE requester_name = %s"
        )
        stored_request = None
        with db.cursor_context(True) as cur:
            cur.execute(query, (self.username,))
            self.assertEqual(cur.rowcount, 1)
            stored_request = cur.fetchone()
        self.assertIsNotNone(stored_request)
        self.assertEqual(stored_request['requester_id'], self.user_id)
        self.assertEqual(stored_request['requestee_name'], self.profile_name)
        self.assertEqual(stored_request['requestee_id'], self.profile_id)

    def test_friend_accept(self):
        """WebSocket: /socket.io/friend-accept"""
        award_category = 'friends'
        signal, data = self.socket_emit_receive({
            'emit-name': 'friend-accept',
            'user_id': self.profile_id,
        })
        self.assertEqual(signal, 'friend-accepted')
        self.assertIn('requester', data)
        self.assertIn('won_awards', data)
        if data['won_awards'] is not None:
            select_award_id_query = (
                "SELECT award_id FROM awards WHERE award_name = %s"
            )
            with db.cursor_context() as cur:
                cur.execute(select_award_id_query, (data['won_awards'],))
                self.assertEqual(cur.rowcount, 1)
                self.awards.append(cur.fetchone()[0])
        self.assertEqual(data['requester'], self.profile_name)
        with db.cursor_context() as cur:
            union_query = (
                "(SELECT username1 FROM friends "
                "WHERE userid2 = %s) "
                "UNION "
                "(SELECT username2 FROM friends "
                "WHERE userid1 = %s)"
            )
            cur.execute(union_query, (self.profile_id,)*2)
            stored_friends = [row[0] for row in cur.fetchall()]
            self.assertIn(self.username, stored_friends)
            cur.execute(union_query, (self.user_id,)*2)
            self.assertEqual(cur.rowcount, 1)
            self.assertEqual(cur.fetchone()[0], self.profile_name)
            requests_query = (
                "SELECT count(*) FROM friend_requests "
                "WHERE requester_id = %s OR requestee_id = %s"
            )
            cur.execute(requests_query, (self.user_id,)*2)
            self.assertEqual(cur.fetchone()[0], 0)

    def test_get_friend_requests(self):
        """WebSocket: /socket.io/get-friend-requests"""
        insert_friend_requests_query = (
            "INSERT INTO friend_requests "
            "(requester_id, requester_name, requester_icon, "
            "requestee_id, requestee_name) "
            "VALUES "
            "(%(requester_id)s, %(requester_name)s, %(requester_icon)s, "
            "%(requestee_id)s, %(requestee_name)s)"
        )
        with db.cursor_context() as cur:
            cur.execute(insert_friend_requests_query, {
                'requester_id': self.user_id,
                'requester_name': self.username,
                'requester_icon': self.user_icon,
                'requestee_id': self.profile_id,
                'requestee_name': self.profile_name,
            })
        signal, data = self.socket_emit_receive({
            'emit-name': 'get-friend-requests',
        })
        self.assertEqual(signal, 'friend-requests')
        self.assertIn('friend_requests', data)
        self.assertIn('sent', data)
        self.assertFalse(data['sent'])
        self.assertEqual(type(data['friend_requests']), list)
        self.assertEqual(len(data['friend_requests']), 0)
        with db.cursor_context() as cur:
            cur.execute(insert_friend_requests_query, {
                'requester_id': self.profile_id,
                'requester_name': self.profile_name,
                'requester_icon': self.profile_icon,
                'requestee_id': self.user_id,
                'requestee_name': self.username,
            })
        signal, data = self.socket_emit_receive({
            'emit-name': 'get-friend-requests',
        })
        self.assertEqual(signal, 'friend-requests')
        self.assertIn('friend_requests', data)
        self.assertIn('sent', data)
        self.assertFalse(data['sent'])
        self.assertEqual(type(data['friend_requests']), list)
        self.assertEqual(len(data['friend_requests']), 1)
        self.assertEqual(len(data['friend_requests'][0]), 3)
        self.assertTupleEqual(data['friend_requests'][0],
                             (self.profile_id,
                              self.profile_name,
                              self.profile_icon))
    
    def test_get_friend_list(self):
        """WebSocket: /socket.io/get-friend-list"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'get-friend-list',
        })
        self.assertEqual(signal, 'friend-list')
        self.assertIn('friends', data)
        self.assertEqual(len(data['friends']), 0)
        insert_friends_query = (
            "INSERT INTO friends "
            "(userid1, username1, icon1, "
            "userid2, username2, icon2) "
            "VALUES "
            "(%(userid1)s, %(username1)s, %(icon1)s, "
            "%(userid2)s, %(username2)s, %(icon2)s)"
        )
        with db.cursor_context() as cur:
            cur.execute(insert_friends_query, {
                'userid1': self.user_id,
                'username1': self.username,
                'icon1': self.user_icon,
                'userid2': self.profile_id,
                'username2': self.profile_name,
                'icon2': self.profile_icon,
            })
        signal, data = self.socket_emit_receive({
            'emit-name': 'get-friend-list',
        })
        self.assertEqual(signal, 'friend-list')
        self.assertIn('friends', data)
        self.assertEqual(len(data['friends']), 1)
        self.assertListEqual(data['friends'][0],
                             [self.profile_name, self.profile_icon])

    def test_userlist(self):
        """WebSocket: /socket.io/userlist"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'userlist',
        })
        self.assertEqual(signal, 'user-listing')
        self.assertIn('userlist', data)
        self.assertEqual(len(data['userlist']), 12)
        first_user = data['userlist'][0][0]  # username of most recently active
        first_icon = data['userlist'][0][1]  # profile_pic
        first_user_id = None
        with db.cursor_context() as cur:
            count_friends_query = (
                "SELECT count(*) FROM friends "
                "WHERE userid1 = %s OR userid2 = %s"
            )
            cur.execute(count_friends_query, (self.user_id,)*2)
            self.assertEqual(cur.fetchone()[0], 0)
            select_user_id_query = (
                "SELECT user_id FROM users WHERE username = %s"
            )
            cur.execute(select_user_id_query, (first_user,))
            self.assertEqual(cur.rowcount, 1)
            first_user_id = cur.fetchone()[0]
        self.assertIsNotNone(first_user_id)
        insert_friends_query = (
            "INSERT INTO friends "
            "(userid1, username1, icon1, "
            "userid2, username2, icon2) "
            "VALUES "
            "(%(userid1)s, %(username1)s, %(icon1)s, "
            "%(userid2)s, %(username2)s, %(icon2)s)"
        )
        with db.cursor_context() as cur:
            cur.execute(insert_friends_query, {
                'userid1': self.user_id,
                'username1': self.username,
                'icon1': self.user_icon,
                'userid2': first_user_id,
                'username2': first_user,
                'icon2': first_icon,
            })
        signal, data = self.socket_emit_receive({
            'emit-name': 'userlist',
        })
        self.assertEqual(signal, 'user-listing')
        self.assertIn('userlist', data)
        self.assertEqual(len(data['userlist']), 12)
        new_first_user = data['userlist'][0][0]
        new_first_icon = data['userlist'][0][1]
        new_first_user_id = None
        with db.cursor_context() as cur:
            count_friends_query = (
                "SELECT count(*) FROM friends "
                "WHERE userid1 = %s OR userid2 = %s"
            )
            cur.execute(count_friends_query, (self.user_id,)*2)
            self.assertEqual(cur.fetchone()[0], 1)
            select_user_id_query = (
                "SELECT user_id FROM users WHERE username = %s"
            )
            cur.execute(select_user_id_query, (new_first_user,))
            self.assertEqual(cur.rowcount, 1)
            new_first_user_id = cur.fetchone()[0]
        self.assertIsNotNone(new_first_user_id)
        self.assertNotEqual(new_first_user_id, first_user_id)
        self.assertNotEqual(new_first_user, first_user)

    def test_populate_scribble(self):
        """WebSocket: /socket.io/populate-scribble"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'scribble',
            'data': self.scribble_message,
            'scribblee_name': self.profile_name,
            'scribblee_id': self.profile_id,
        })
        self.assertEqual(signal, 'scribble-response')
        self.assertIn('data', data)
        self.assertIn('user', data)
        self.assertEqual(data['user'], self.username)
        self.assertEqual(data['data'], self.scribble_message)
        signal, data = self.socket_emit_receive({
            'emit-name': 'populate-scribble',
            'scribblee': self.profile_name,
        })
        self.assertEqual(signal, 'scribble-populate')
        for field in ('user', 'timestamp', 'comment'):
            self.assertIn(field, data)
        
    def test_socket_scribble(self):
        """WebSocket: /socket.io/scribble"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'scribble',
            'data': self.scribble_message,
            'scribblee_name': self.profile_name,
            'scribblee_id': self.profile_id,
        })
        self.assertEqual(signal, 'scribble-response')
        self.assertIn('data', data)
        self.assertIn('user', data)
        self.assertEqual(data['user'], self.username)
        self.assertEqual(data['data'], self.scribble_message)

    def test_populate_chatbox(self):
        """WebSocket: /socket.io/populate-chatbox"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'populate-chatbox',
        })
        self.assertEqual(signal, 'chat-populate')
        for field in ('user', 'timestamp', 'comment'):
            self.assertIn(field, data)

    def test_socket_message(self):
        """WebSocket: /socket.io/chat"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'chat',
            'data': self.chat_message,
        })
        self.assertEqual(signal, 'chat-response')
        self.assertIn('data', data)
        self.assertIn('user', data)
        self.assertEqual(data['user'], self.username)
        self.assertEqual(data['data'], self.chat_message)

    def tearDown(self):
        delete_friends_queries = ((
            "DELETE FROM friend_requests "
            "WHERE requestee_name = %s OR requester_name = %s"
        ),
            "DELETE FROM friends WHERE username1 = %s OR username2 = %s",
        )
        delete_awards_queries = (
            "UPDATE award_tracking SET number_completed = 0 WHERE user_id = %s",
            "DELETE FROM award_winners WHERE user_id = %s",
        )
        delete_chat_query = "DELETE FROM chatbox WHERE user_id = %s"
        delete_scribble_query = (
            "DELETE FROM scribble WHERE scribbler_id = %s OR scribblee_id = %s"
        )
        with db.cursor_context() as cur:
            cur.execute(delete_chat_query, (self.user_id,))
            cur.execute(delete_scribble_query, (self.user_id,)*2)
            for query in delete_friends_queries:
                cur.execute(query, (self.username,)*2)
            for query in delete_awards_queries:
                cur.execute(query, (self.user_id,))
            if self.awards:
                reset_winners_query = (
                    "UPDATE awards "
                    "SET number_of_winners = number_of_winners - 1 "
                    "WHERE award_id = %s "
                    "RETURNING number_of_winners"
                )
                count_winners_query = (
                    "SELECT number_of_winners FROM awards WHERE award_id = %s"
                )
                for award in self.awards:
                    cur.execute(reset_winners_query, (award,))
                    self.assertEqual(cur.rowcount, 1)
                    number_of_winners = cur.fetchone()[0]
                    cur.execute(count_winners_query, (award,))
                    self.assertEqual(cur.fetchone()[0], number_of_winners)
                    self.assertGreaterEqual(number_of_winners,
                                            self.initial_winners[award])
        select_friends_queries = ((
            "SELECT count(*) FROM friend_requests "
            "WHERE requestee_name = %s OR requester_name = %s"
        ), (
            "SELECT count(*) FROM friends "
            "WHERE username1 = %s OR username2 = %s"
        ))
        select_awards_queries = ((
            "SELECT max(number_completed) FROM award_tracking "
            "WHERE user_id = %s"
        ),
            "SELECT count(*) FROM award_winners WHERE user_id = %s",
        )
        with db.cursor_context() as cur:
            for query in select_friends_queries:
                cur.execute(query, (self.username,)*2)
                self.assertEqual(cur.fetchone()[0], 0)
            for query in select_awards_queries:
                cur.execute(query, (self.user_id,))
                self.assertEqual(cur.fetchone()[0], 0)

if __name__ == '__main__':
    unittest.main()
