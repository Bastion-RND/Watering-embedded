import ujson
import os

a, b = 5, 9
default_json_struct = {"name" : "Lora", "humidity": [a, b]}

try: 
    with open("data.json", "r") as f:
        json_struct = ujson.load(f)
except:
    with open("data.json", "w") as f:
        f.write(ujson.dumps(default_json_struct))

json_struct["name"] = "cock"
with open("data.json", "w") as f:
        f.write(ujson.dumps(json_struct))
with open("data.json", "r") as f:
        print(ujson.load(f))