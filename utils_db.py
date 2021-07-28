import shelve
import sys

# args
db_name = sys.argv[1]
action = sys.argv[2]

# shelve db
db = shelve.open(db_name.split(".")[0], writeback=True)
db_keys = list(db.keys())
db_keys.sort()

# actions
if action == "print":
    for k in db_keys:
        print(k, db[k])
elif action == "remove":
    entry = sys.argv[3]
    del db[entry]

db.close()
