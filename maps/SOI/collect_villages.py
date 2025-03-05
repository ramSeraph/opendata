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

name_fields = [ 'VILLAGE', 'VillageNam', 'VillNam', 'VT_NAME', 'SOI_NAME', 'Vill_name', 'Vill_nasme', 'Vill_nane', 'Viil_name', 'Vill_Name', 'VIll_name' ]

paths = Path('data/raw/villages/').glob('**/*.geojsonl')
out = []
with open('SOI_villages.geojsonl', 'w') as of:
    for path in paths:
        print(path)
        feats = []
        with open(path, 'r') as f:
            for line in f:
                feat = json.loads(line)
                feats.append(feat)
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
    
            if vill is not None:
                props['VILLAGE'] = fix_soi_string(vill)
                props['VILLAGE_C'] = unidecode.unidecode(props['VILLAGE'])
            else:
                props['VILLAGE'] = None
                props['VILLAGE_C'] = None
    
            subdist = None
            if 'TEHSIL' in props:
                sudist = props['TEHSIL']
            elif 'Sub_dis' in props:
                sudist = props['Sub_dis']
            elif 'Sub_dist' in props:
                sudist = props['Sub_dist']
            elif 'Siub_dist' in props:
                sudist = props['Siub_dist']
            elif 'Sud_dist' in props: 
                sudist = props['Sud_dist']
            elif 'Sub_Dist' in props: 
                sudist = props['Sub_Dist']
            elif 'Sub_Dist' in props: 
                sudist = props['Sub_Dist']
            else:
                print(props)
    
            dist = None
            if 'DISTRICT' in props:
                dist = props['DISTRICT']
            elif 'District' in props:
                dist = props['District']
            elif 'district' in props:
                dist = props['district']
            elif 'DIstrict' in props:
                dist = props['DIstrict']
            else:
                print('missing district', props)
            #if 'STATE' not in props:
            #    print(props)
    
            state = None
            if 'STATE' in props:
                state = props['STATE']
            elif 'STATE_UT' in props:
                state = props['STATE_UT']
            else:
                print('missing state', props)
            
            props['DISTRICT'] = fix_soi_string(dist)
            if 'District' in props:
                del props['District']
            elif 'district' in props:
                del props['district']
            elif 'DIstrict' in props:
                del props['DIstrict']
    
            if props['DISTRICT'] is not None:
                props['DISTRICT_C'] = unidecode.unidecode(props['DISTRICT'])
            else:
                props['DISTRICT_C'] = None
    
            props['SUBDISTRICT'] = fix_soi_string(subdist)
            if 'TEHSIL' in props:
                del props['TEHSIL']
            elif 'Sub_dis' in props:
                del props['Sub_dis']
            elif 'Sub_dist' in props:
                del props['Sub_dist']
            elif 'Siub_dist' in props:
                del props['Siub_dist']
            elif 'Sud_dist' in props: 
                del props['Sud_dist']
            elif 'Sub_Dist' in props: 
                del props['Sub_Dist']
            elif 'Sub_Dist' in props: 
                del props['Sub_Dist']
    
            if props['SUBDISTRICT'] is not None:
                props['SUBDISTRICT_C'] = unidecode.unidecode(props['SUBDISTRICT'])
            else:
                props['SUBDISTRICT_C'] = None
    
            props['STATE'] = fix_soi_string(state)
            if 'STATE_UT' in props:
                del props['STATE_UT']
            if props['STATE'] is not None:
                props['STATE_C'] = unidecode.unidecode(props['STATE'])
            else:
                props['STATE_C'] = None
    
            of.write(json.dumps(feat, ensure_ascii=False) + '\n')
