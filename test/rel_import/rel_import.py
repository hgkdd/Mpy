import config

cdict = {"a": 4711}

print(cdict)

cdict.update(config.cdict)

print(cdict)
