from cherrydoor import api, Resource, current_user, parser, dt, inputs, mongo

parser.add_argument('time_from', help='start of time range')
parser.add_argument('time_to', help='end of time range')
parser.add_argument('username', help='username of requested user')
parser.add_argument('card', help='MiFare card uid')

class Stats(Resource):
    '''
    Usage statistics. Accesible on `/api/stats` and `/api/stats/<string:time_from>/<string:time_to>` endpoint
    '''
    def get(self, time_from=None, time_to=None):
        '''
        If http GET is used, the api will return list of logs with range determined by request parameters `time_from` and `time_to` or in url (iso8601 formatted).
        When no parameters are present, this method will retuen logs between 7 days ago and today
        Logs are retrived from `logs` collection and need to contain `timestamp` field with a valid datetime as a value.
        '''
        if not current_user.is_authenticated:
            return {'error':'Not Authenticated'}, 401
        params=parser.parse_args()
        try:
            time_from = inputs.datetime_from_iso8601(time_from)
            time_to = inputs.datetime_from_iso8601(time_to)
        except AttributeError:
            try:
                time_from = inputs.datetime_from_iso8601(params['time_from'])
            except (AttributeError, KeyError):
                time_from = dt.date.today()-dt.timedelta(days=7)   
            try:
                time_to = inputs.datetime_from_iso8601(params['time_to'])
            except (AttributeError, KeyError):
                time_to = dt.datetime.now()
        try:
            results = [result for result in mongo.logs.find({'timestamp': {'$lt':time_to, '$gte':time_from}}, {'card':0, '_id':0})]
            return results, 200
        except:
            return [], 404
        
    
class Card(Resource):
    '''
    Card management and retrival. Accesible on `/api/card/<card>` and `/api/card` endpoints.
    '''
    def get(self, card=None):
        '''
        If HTTP GET is used, check if the card uid (passed in url or in request body as `card`) is associated with any user
        '''
        if not current_user.is_authenticated:
            return {'error':'Not Authenticated'}, 401
        params=parser.parse_args()
        if not card:
            try:
                card = params['card']
                if card==None:
                    raise KeyError
            except KeyError:
                return None, 400
        try:
            username = params['username']
            if username==None:
                raise KeyError
            result = mongo.users.find_one_or_404({'name':username, 'cards':card}, {'password':0, '_id':0})
        except KeyError:
            result = mongo.users.find_one_or_404({'cards':card}, {'password':0, '_id':0})
        return result, 200
    def post(self, card=None):
        '''
        If HTTP POST is used, add the card to a user.
        User is determined by `username` passed in request body.
        If there is no `username` present, current user is modified.
        '''
        if not current_user.is_authenticated:
            return {'error':'Not Authenticated'}, 401
        params=parser.parse_args()
        
        if not card:
            try:
                card = params['card']
                if card==None:
                    raise KeyError
            except KeyError:
                return {'error':'no card specified. Pass card uid in url or as `card` in request body'}, 400
        try:
            username = params['username']
            if username==None:
                    raise KeyError
        except KeyError:
            current_user.add_card(card)
            return True, 201
        mongo.users.find_one_and_update({'name':username}, {'$push':{'cards':card}})
        return True, 201
    def delete(self, card=None):
        '''
        If HTTP DELETE is used, delete the card from database of users.
        User is determined by `username` passed in request body.
        If there is no `username` present, card will be removed from any and all users that it's associated with.
        If `*` is passed as username, returns all users.
        '''
        if not current_user.is_authenticated:
            return {'error':'Not Authenticated'}, 401
        params=parser.parse_args()
        
        if not card:
            try:
                card = params['card']
                if card==None:
                    raise KeyError
            except KeyError:
                return {'error':'no card specified. Pass card uid in url or as `card` in request body'}, 400
        try:
            username = params['username']
            if username==None:
                    raise KeyError
            mongo.users.find_one_and_update({'name':username}, {'$pull':{'cards':card}})
            return True, 200
        except KeyError:
            mongo.users.update({}, {'$pull':{'cards':card}})
            return True, 200

class UserAPI(Resource):
    '''
    User data management and retrieval. Accesible on `api/user/<username>` and `/api/user` endpoints.
    '''
    def get(self, username=None):
        '''
        If HTTP GET is used, see if user with username passed in url or in request body (as `username`) exists and return their username and cards associated with them.
        When no user with request username exists, return 404 status code
        '''
        if not current_user.is_authenticated:
            return {'error':'Not Authenticated'}, 401
        if not username:
            params=parser.parse_args()
            try:
                username = params['username']
                if username==None:
                    raise KeyError
            except KeyError:
                return None, 400
        if username == "*":
            result = list(mongo.users.find({}, {'password':0, '_id':0}))
            return result, 200
        result = mongo.users.find_one_or_404({'name':username}, {'password':0, '_id':0})
        return result, 200
    def post(self, username=None):
        '''
        If HTTP POST is used, create a passwordless user (unable to manage the door, able to enter)
        '''
        if not current_user.is_authenticated:
            return {'error':'Not Authenticated'}, 401
        params=parser.parse_args()
        if not username:
            try:
                username = params['username']
                if username==None:
                    raise KeyError
            except KeyError:
                return None, 400
        try:
            card = params['card']
            if card==None:
                    raise KeyError
        except KeyError:
            card=''
        mongo.users.update_one({'name':username}, {'$set':{'name':username, 'cards':[card]}}, upsert=True)
        return None, 201
    def delete(self, username=None):
        '''
        If HTTP DELETE is used, delete the specified user
        '''
        if not current_user.is_authenticated:
            return {'error':'Not Authenticated'}, 401
        params=parser.parse_args()
        if not username:
            try:
                username = params['username']
                if username==None:
                    raise KeyError
            except KeyError:
                return None, 400
        mongo.users.delete_one({'name':username})
        return None, 204

api.add_resource(Stats, '/api/stats', '/api/stats/<string:time_from>/<string:time_to>')
api.add_resource(UserAPI, '/api/user/<string:username>', '/api/user')
api.add_resource(Card, '/api/card/<string:card>', '/api/card')