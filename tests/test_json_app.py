import sys
sys.path[0:0] = [""]

import unittest
import datetime
import flask

from flask.ext.mongoengine import MongoEngine
from . import FlaskMongoEngineTestCase

class JSONAppTestCase(FlaskMongoEngineTestCase):

    def dictContains(self,superset,subset):
        for k,v in subset.items():
            if not superset[k] == v:
                return False
        return True

    def assertDictContains(self,superset,subset):
        return self.assertTrue(self.dictContains(superset,subset))

    def setUp(self):
        super(JSONAppTestCase, self).setUp()
        self.app.config['MONGODB_DB'] = 'testing'
        self.app.config['TESTING'] = True
        db = MongoEngine()

        class Todo(db.Document):
            title = db.StringField(max_length=60)
            text = db.StringField()
            done = db.BooleanField(default=False)
            pub_date = db.DateTimeField(default=datetime.datetime.now)

        db.init_app(self.app)

        Todo.drop_collection()
        self.Todo = Todo

        @self.app.route('/')
        def index():
            return flask.jsonify(result=self.Todo.objects())

        @self.app.route('/add', methods=['POST'])
        def add():
            form = flask.request.form
            todo = self.Todo(title=form['title'],
                             text=form['text'])
            todo.save()
            return flask.jsonify(result=todo)

        @self.app.route('/show/<id>/')
        def show(id):
            return flask.jsonify(result=self.Todo.objects.get_or_404(id=id))

        self.db = db


    def test_connection_kwargs(self):
        self.app.config['MONGODB_SETTINGS'] = {
            'DB': 'testing_tz_aware',
            'ALIAS': 'tz_aware_true',
            'TZ_AWARE': True,
        }
        self.app.config['TESTING'] = True
        db = MongoEngine()
        db.init_app(self.app)
        self.assertTrue(db.connection.tz_aware)

        db = MongoEngine()
        self.app.config['MONGODB_SETTINGS'] = {
            'DB': 'testing',
            'alias': 'tz_aware_false',
        }
        db.init_app(self.app)
        self.assertFalse(db.connection.tz_aware)

    def test_connection_kwargs_with_false_values(self):
        self.app.config['MONGODB_SETTINGS'] = {
            'DB': 'testing',
            'alias': 'test',
            'use_greenlets': False
        }
        self.app.config['TESTING'] = True
        db = MongoEngine()
        db.init_app(self.app)
        self.assertFalse(db.connection.use_greenlets)

    def test_with_id(self):
        c = self.app.test_client()
        resp = c.get('/show/38783728378090/')
        self.assertEqual(resp.status_code, 404)

        rv = c.post('/add', data={'title': 'First Item', 'text': 'The text'})
        self.assertEqual(rv.status_code,200)

        resp = c.get('/show/%s/' % self.Todo.objects.first().id)
        self.assertEqual(resp.status_code, 200)
        res = flask.json.loads(resp.data).get('result')
        self.assertDictContains(res,{
                'title': 'First Item',
                'text': 'The text'
            })

    def test_basic_insert(self):
        c = self.app.test_client()
        d1 = {'title': 'First Item', 'text': 'The text'}
        d2 = {'title': '2nd Item', 'text': 'The text'}
        c.post('/add', data=d1)
        c.post('/add', data=d2)
        rv = c.get('/')
        result = flask.json.loads(rv.data).get('result')

        self.assertEqual(len(result),2)

        # ensure each of the objects is one of the two we already
        # inserted
        for obj in result:
            self.assertTrue(any([
                self.dictContains(obj,d1),
                self.dictContains(obj,d2)
                ]))
