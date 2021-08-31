import shelve
import sys
import json
import time

# args
db_name = sys.argv[1]
action = sys.argv[2]

# shelve db
db = shelve.open(db_name.split(".")[0], writeback=True)
if not 'count' in db:
    db['count'] = 0

db_keys = list(db.keys())
db_keys.sort()

# Read DB
if action == "print":
    for k in db_keys:
        print(k, db[k])

# Remove entry from DB
elif action == "remove":
    entry = sys.argv[3]
    del db[entry]

# Add entries to DB
elif action == "insert":
    f = open(sys.argv[3],'r')
    collections = json.load(f)
    f.close()
    for c in collections:
        if "collection" not in c:
            continue
        count = str(db['count'])
        print("count = "+count)

        signature = collections[c]
        new_id = "document"+ count + "_" + str(signature["x"]) + "_" + str(signature["y"]) + "_" + signature["comment"] + "_" + signature["map"]
#         signature = signature[list(signature.keys())[0]]
#         print(signature)
        print(new_id)
        db[new_id] = {
                "document": new_id,
                "signature": signature}

#             db["document"+count] = new_doc
        db["count"] += 1
#         time.sleep(1)
        db_keys.sort()
        print(list(db.keys()))


db.close()
