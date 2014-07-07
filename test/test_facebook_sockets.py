from dyffy.utils import *
from dyffy import app, db, sockets
import unittest
from socket_test import SocketTest

class TestFacebookProfileData(SocketTest):

    def setUp(self):
        SocketTest.setUp(self)
        self.fb_id = 100003733762719
        self.fb_username = 'jack.peterson.100'
        self.first_name = 'Jack'
        self.last_name = 'Peterson'
        self.gender = 'male'
        self.location_id = '000'
        self.location_name = 'Nowhere'
        self.bio = 'Random scrub'
        self.fb_url = 'http://www.facebook.com/'
        self.fb_graph_url = 'http://graph.facebook.com/'
        self.link = self.fb_url + self.fb_username
        self.picture = self.fb_graph_url + str(self.fb_id) + \
                       '/picture?type=large'

    def test_facebook_profile_data(self):
        """WebSocket: /socket.io/facebook-profile-data"""
        with self.login():
            intake = {
                'id': self.fb_id,
                'username': self.fb_username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'gender': self.gender,
                'location_id': self.location_id,
                'location_name': self.location_name,
                'bio': self.bio,
                'link': self.link,
                'picture': self.picture,
            }
            sockets.facebook_profile_data(intake)
        select_fb_id_query = (
            "SELECT user_fb_id, user_fb_name, firstname, lastname, gender, "
            "location, biography, facebook_url, profile_pic, fb_connect "
            "FROM users WHERE username = %s"
        )
        columns = ('user_fb_id', 
                   'user_fb_name', 
                   'firstname',
                   'lastname',
                   'gender',
                   'location',
                   'biography',
                   'facebook_url',
                   'profile_pic',
                   'fb_connect')
        nullable_columns = ('user_fb_name', 
                            'firstname',
                            'lastname',
                            'gender',
                            'location',
                            'biography')
        with db.cursor_context(True) as cur:
            cur.execute(select_fb_id_query, (self.username,))
            self.assertEqual(cur.rowcount, 1)
            data = cur.fetchone()
            print data
            for col in columns:
                self.assertIn(col, data)
                if col not in nullable_columns:
                    self.assertIsNotNone(data[col])

    def tearDown(self):
        update_users_query = (
            "UPDATE users "
            "SET firstname = NULL, lastname = NULL, "
            "gender = NULL, location = NULL, "
            "biography = NULL, facebook_url = NULL, "
            "profile_pic = NULL, user_fb_id = NULL, "
            "user_fb_name = NULL, fb_connect = NULL "
            "WHERE username = %s"
        )
        with db.cursor_context() as cur:
            cur.execute(update_users_query, (self.username,))
        select_user_query = (
            "SELECT count(*) FROM users "
            "WHERE username = %s AND fb_connect IS NOT NULL"
        )
        with db.cursor_context() as cur:
            cur.execute(select_user_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 0)


class TestRecordFacebookFriends(SocketTest):

    def setUp(self):
        SocketTest.setUp(self)
        self.old_friend = {
            'id': 708070107,
            'name': 'Mark McCormick',
        }
        self.new_friend = {
            'id': 28300439,
            'name': 'Reggie Goolsby',
        }
        delete_query = "DELETE FROM facebook_friends WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(delete_query, (self.username,))
        insert_old_friend_query = (
            "INSERT INTO facebook_friends "
            "(username, friend_fb_id, friend_fb_name) "
            "VALUES (%s, %s, %s)"
        )
        with db.cursor_context() as cur:
            cur.execute(insert_old_friend_query,
                        (self.username,
                         self.old_friend['id'],
                         self.old_friend['name']))

    def test_record_facebook_friends(self):
        """WebSocket: /socket.io/record-facebook-friends"""
        with self.login():
            intake = {
                'friends': [self.old_friend, self.new_friend],
            }
            sockets.record_facebook_friends(intake)

    def tearDown(self):
        delete_query = "DELETE FROM facebook_friends WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(delete_query, (self.username,))
            self.assertEqual(cur.rowcount, 2)
        select_query = (
            "SELECT count(*) FROM facebook_friends WHERE username = %s"
        )
        with db.cursor_context() as cur:
            cur.execute(select_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 0)


class TestSelectPic(SocketTest):

    def setUp(self):
        SocketTest.setUp(self)
        self.win_friend = {
            'id': 708070107,
            'name': 'Mark McCormick',
        }
        self.lose_friend = {
            'id': 28300439,
            'name': 'Reggie Goolsby',
        }
        insert_friend_query = (
            "INSERT INTO facebook_friends "
            "(username, friend_fb_id, friend_fb_name) "
            "VALUES (%s, %s, %s)"
        )
        with db.cursor_context() as cur:
            for friend in (self.win_friend, self.lose_friend):
                cur.execute(insert_friend_query,
                            (self.username,
                             friend['id'],
                             friend['name']))

    def test_select_pic(self):
        """WebSocket: /socket.io/select-pic"""
        with self.login():
            intake = {
                'target': self.win_friend['id'],
                'untarget': self.lose_friend['id'],
            }
            sockets.select_pic(intake)
        select_rating_query = (
            "SELECT friend_fb_id, friend_fb_name, rating "
            "FROM facebook_friends WHERE username = %s"
        )
        with db.cursor_context(True) as cur:
            cur.execute(select_rating_query, (self.username,))
            self.assertEqual(cur.rowcount, 2)
            for row in cur:
                if row['friend_fb_id'] == self.win_friend['id']:
                    self.assertEqual(row['friend_fb_name'],
                                     self.win_friend['name'])
                    self.assertEqual(row['rating'], 1)
                else:
                    self.assertEqual(row['friend_fb_name'],
                                     self.lose_friend['name'])
                    self.assertEqual(row['rating'], -1)

    def tearDown(self):
        delete_query = "DELETE FROM facebook_friends WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(delete_query, (self.username,))
            self.assertEqual(cur.rowcount, 2)
        select_query = (
            "SELECT count(*) FROM facebook_friends WHERE username = %s"
        )
        with db.cursor_context() as cur:
            cur.execute(select_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()