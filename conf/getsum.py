import json

with open("secret-neopets") as f:
    data = json.loads(f.read())

npinbank_count = 0
npinbank = 0
nponhand_count = 0
nponhand = 0
for user, values in data.items():
    for item, value in values.items():
        if item == "nponhand":
            try:
                if int(str(value)) >= 0:
                    nponhand += int(str(value))
                    nponhand_count += 1
            except:
                pass
        if item == "npinbank":
            try:
                if int(str(value)) >= 0:
                    npinbank += int(str(value))
                    npinbank_count += 1
            except:
                pass

totalnp = npinbank + nponhand
totalacc = max(npinbank_count, nponhand_count)
print(f"NP in bank:\t{npinbank:,} NP\tover {npinbank_count} accounts")
print(f"NP on hand:\t{nponhand:,} NP\tover {nponhand_count} accounts")
print(f"Total NP:\t{totalnp:,} NP\tover {totalacc} accounts")

