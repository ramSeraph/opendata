from pathlib import Path

def fix_soi_string(v):
    if v == None:
        v = 'UNKNOWN'
    v = v.replace(">", "A")
    v = v.replace("<", "a")
    v = v.replace("|", "I")
    v = v.replace("\\", "i")
    v = v.replace("@", "U")
    v = v.replace("#", "u")
    return v
 
for p in Path('data/raw/villages/').glob('*/*/*.osm'):
    p.rename(fix_soi_string(str(p)))
    #print(fix_soi_string(str(p)))
    

