import json
import unidecode

from pathlib import Path

def fix_soi_string(v):
    if v == None:
        return v
    v = v.replace(">", "Ā")
    v = v.replace("<", "ā")
    v = v.replace("|", "Ī")
    v = v.replace("\\", "ī")
    v = v.replace("@", "Ū")
    v = v.replace("#", "ū")
    return v

name_fields = [ 'VILLAGE', 'VillageNam', 'VillNam', 'VT_NAME', 'SOI_NAME' ]

paths = Path('data/raw/villages/').glob('*/*/data.geojson')
out = []
for path in paths:
    data = json.loads(path.read_text())
    feats = data['features']
    for feat in feats:
        props = feat['properties']
        vill = None
        not_found = True
        for k in name_fields:
            if k in props:
                vill = props[k]
                not_found = False
                break

        if not_found:
            print(props)
            if props['DISTRICT'] in [ 'ARWAL', 'AR>RIA']:
                continue
        if vill is not None:
            props['VILLAGE'] = fix_soi_string(vill)
            props['VILLAGE_C'] = unidecode.unidecode(props['VILLAGE'])
        else:
            props['VILLAGE'] = None
            props['VILLAGE_C'] = None

        if 'TEHSIL' not in props:
            print(props)
        dist = None
        if 'DISTRICT' in props:
            dist = props['DISTRICT']
        elif 'District' in props:
            dist = props['District']
        else:
            print(props)
        #if 'STATE' not in props:
        #    print(props)

        
        props['DISTRICT'] = fix_soi_string(dist)
        if 'District' in props:
            del props['District']
        if props['DISTRICT'] is not None:
            props['DISTRICT_C'] = unidecode.unidecode(props['DISTRICT'])
        else:
            props['DISTRICT_C'] = None
        props['TEHSIL'] = fix_soi_string(props.get('TEHSIL', None))
        if props['TEHSIL'] is not None:
            props['TEHSIL_C'] = unidecode.unidecode(props['TEHSIL'])
        else:
            props['TEHSIL_C'] = None
        props['STATE'] = fix_soi_string(props.get('STATE', None))
        if props['STATE'] is not None:
            props['STATE_C'] = unidecode.unidecode(props['STATE'])
        else:
            props['STATE_C'] = None

        out.append(feat)

with open('SOI_villages.geojsonl', 'w') as f:
    for feat in out:
        f.write(json.dumps(feat, ensure_ascii=False) + '\n')
