from pymongo import MongoClient

def connect_train() :
    client = MongoClient('localhost', 27017)
    db = client.tanks.train
    return db

def load_train(training):
    training = {}
    train_collection = connect_train()
    trains = train_collection.find()
    for train in trains :
        training[train['N']] = (train['dist'], train['x'], train['y'], train['angle'])
    return training

def save_train(training):
    train_collection = connect_train()
    for key in training :
        dist = training[key][0]
        x = training[key][1]
        y = training[key][2]
        angle = training[key][3]
        train_collection.update({'N':key},
                                {'N':key, 'dist':dist, 'x':x, 'y':y, 'angle':angle}, upsert=True)

def connect():
    client = MongoClient('localhost', 27017)
    db = client.tanks.users
    return db


def upload_user(stats):
    db = connect()
    data = db.find_one({"username": stats.username})
    if data:
        stats.killed = data["killed"]
        stats.played_games = data["played_games"]
        stats.died = data["died"]
    else:
        stats.reset_data()
        save_user(stats)


def save_user(stats):
    db = connect()
    db.update({'username': stats.username},
              {'username': stats.username,
               'killed': stats.killed, 'died' : stats.died,
               'played_games': stats.played_games}, upsert=True)


def delete_user(username):
    db = connect()
    db.remove({'username': username}, True)

def update_user(username, field, value) :
    value = str(value)
    db = connect()
    query = { "username": username }
    new_value = { "$set" : { field : value } }
    db.find_one(query, new_value, upsert = False)


def get_global_records(field):
    if not field in ['killed', 'died', 'played_games'] :
        raise ValueError('unspecified filed')
    db = connect()
    users = db.find()
    tops = []
    for user in users:
        tops.append(user)
    tops.sort(key = lambda x : x[field], reverse = True)
    n = len(tops)
    return tops[:min(n, Statistics.RECORDS_COUNT)]

class Statistics:
    RECORDS_COUNT = 5

    def __init__(self, username):
        self.username = username
        self.killed = 0
        self.died = 0
        self.played_games = 0
        if username != '' :
            self.upload_user_from_db()

    def upload_user_from_db(self):
        upload_user(self)

    def save_user_to_db(self):
        if self.username != '' :
            save_user(self)

    def reset_data(self):
        self.died = 0
        self.killed = 0
        self.played_games = 0

def main():
    pl1 = Statistics("p1")
    pl1.killed += 1
    pl1.save_user_to_db()
    print(pl1.killed)
    get_global_records('killed')
