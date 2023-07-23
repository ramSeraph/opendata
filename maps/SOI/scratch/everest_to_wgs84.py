import json

# script to convert everet zones into known epsg.. incomplete

# ignores Zone IB completely to simplify things
# also the 88.0 is supposed to be very approximate
def get_everest_epsg(center, year, src):
    if center[1] < 15.0:
        if center[0] > 88:
            zone = 'IVB'
        else:
            zone = 'IVA'
    elif center[1] < 21.0:
        if center[0] > 88.0:
            zone = 'IIIB'
        else:
            zone = 'IIIA'
    elif center[0] > 82.0:
        zone = 'IIB'
    else:
        if center[1] < 28.0:
            zone = 'IIA'
        elif center[1] < 35.5833333:
            zone = 'IA'
        else:
            zone = '0'

    if year < 1975:
        if zone == '0':
            epsg = 24370
        elif zone == 'IA':
            epsg = 24371
        elif zone == 'IIA':
            epsg = 24372
        elif zone == 'IIB':
            epsg = 24382
        elif zone == 'IIIA':
            epsg = 24373
        elif zone == 'iVA':
            epsg = 24374
    else:
        if zone == 'IA':
            epsg = 24378
        elif zone == 'IIA':
            epsg = 24379
        elif zone == 'IIB':
            epsg = 24380
        elif zone == 'IIIA':
            epsg = 24381
        elif zone == 'iVA':
            epsg = 24383
    

if __name__ == '__main__':
    with open('data/index.geojson') as f:
        index_data = json.load(f)
        for f in index_data['features']:
            ibox = f['geometry']['coordinates'][0]
            center = (ibox[0][0] + ibox[2][0])/2.0, (ibox[0][1] + ibox[2][1])/2.0 
            epsg = get_everest_epsg(center, 1985, 'SOI')


        
