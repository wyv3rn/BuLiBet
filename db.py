from collections import defaultdict

from tinydb import TinyDB

def init(storage):
    global betday_cache
    global user_db
    global bet_db
    global match_db

    betday_cache = defaultdict(dict)
    if not storage.endswith('/'):
        storage += '/'
    user_file = storage + 'userdb.json'
    bet_file = storage + 'betdb.json'
    match_file = storage + 'matchdb.json'
    user_db = TinyDB(user_file)
    bet_db = TinyDB(bet_file)
    match_db = TinyDB(match_file)
