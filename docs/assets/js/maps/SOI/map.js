
var bg_style = {
    version: 8,
    sources: {},
    layers: [{
        id: 'background',
        type: 'background',
        paint: { 'background-color': 'black' }
    }]
}

BOUNDS_INDIA = [[61.1113787, 2.5546079], [101.395561, 39.6745457]]

const map = new maplibregl.Map({
    container: 'map', 
    style: bg_style,
    bounds: BOUNDS_INDIA,
    zoom: 1,
    maxBounds: BOUNDS_INDIA,
    minZoom: 1
})
map.addControl(new maplibregl.NavigationControl())
//map.doubleClickZoom.disable()



var gFeatures = null
var gStatusInfo = null
var lookupIndex = null
var indexMap = {}
function setFeatureStates() {
    if (gStatusInfo === null || gFeatures === null) {
        return
    }
    var featureMap = {}
    lookupIndex = new Flatbush(gFeatures.length)
    console.log(gFeatures)
    for (feature of gFeatures) {
        var sheetNum = feature.properties.EVEREST_SH
        featureMap[sheetNum] = feature
        const geom = turf.getGeom(feature)
        const bbox = turf.bbox(geom)
        idx = lookupIndex.add(...bbox)
        indexMap[idx] = feature
    }
    lookupIndex.finish()

    for (var s in gStatusInfo) {
        var featureId = featureMap[s].id
        map.setFeatureState(
            { source: 'tiles', id: featureId },
            gStatusInfo[s]            
        )
    }
}


function updateStatusInfo(statusInfo) {
    gStatusInfo = statusInfo
    console.log(gStatusInfo)
    setFeatureStates()
}


function updateFeatureData(feats) {
    gFeatures = feats
    setFeatureStates()
}

function fetchStatusInfoCb(err, data) {
    if (err !== null) {
        console.log(err)
        var statusSpan = document.getElementById('call_status')
        statusSpan.innerHTML = "Error!! Couldn't get status list"
    } else {
        updateStatusInfo(data)
    }
}


window.onload = (event) => {
    var statusSpan = document.getElementById('call_status')
    statusSpan.innerHTML = ''
    getStatusData(fetchStatusInfoCb)
}


map.on('load', () => {
    map.addSource('tiles', {
        'type': 'geojson',
        'data': 'https://storage.googleapis.com/soi_data/index.geojson',
        'generateId': true
    })
    map.addSource('india-states', {
        'type': 'geojson',
        'data': 'https://raw.githubusercontent.com/datameet/maps/master/website/docs/data/geojson/states.geojson'
    })
    const green = 'green'
    const red = 'red'
    const yellow = 'yellow'

    // Add a new layer to visualize the polygon.
    map.addLayer({
        'id': 'tiles-fill',
        'type': 'fill',
        'source': 'tiles', // reference the data source
        'layout': {},
        'paint': {
            'fill-color': [ 
                'case',
                [ '==', ['feature-state', 'status'], 'parsed'],
                green,
                [ '==', ['feature-state', 'status'], 'not_found'],
                red,
                yellow
            ],
            'fill-opacity': 0.5
        },
    })
    // Add a black outline around the polygon.
    map.addLayer({
        'id': 'tiles-outline',
        'type': 'line',
        'source': 'tiles',
        'layout': {},
        'paint': {
            'line-color': '#000',
            'line-width': 0.5
        }
    })
    // Add a black outline around the polygon.
    map.addLayer({
        'id': 'india-states-fill',
        'type': 'fill',
        'source': 'india-states',
        'layout': {},
        'paint': {
            'fill-color': '#000',
            'fill-opacity': 0.0
        }
    })

    // Add a black outline around the polygon.
    map.addLayer({
        'id': 'india-states-outline',
        'type': 'line',
        'source': 'india-states',
        'layout': {},
        'paint': {
            'line-color': '#000',
            'line-width': 1
        }
    })
})

map.once('idle', () => {
    const features = map.querySourceFeatures('tiles')
    var alreadySeen = new Set()
    var filtered = []
    for (f of features) {
        const sheetNum = f.properties.EVEREST_SH
        if (alreadySeen.has(sheetNum)) {
            continue
        }
        alreadySeen.add(sheetNum)
        filtered.push(f)
    }
    updateFeatureData(filtered)
})

map.on('click', 'tiles-fill', (e) => {
    var feature = e.features[0]
    var fstate = map.getFeatureState({ id: feature.id,
                                       source: 'tiles'})
    var sheetNo = feature.properties.EVEREST_SH
    var html = `<b>${sheetNo}</b><br>`
    if ('pdfUrl' in fstate) {
        //html += '<br>'
        html += ' '
        html += `<a target="_blank" href=${fstate.pdfUrl}>pdf</a>`
    }
    if ('gtiffUrl' in fstate) {
        if (!('pdfUrl' in fstate)) {
            // html += '<br>'
            html += ' '
        } else {
            html += ' '
        }
        html += `<a target="_blank" href=${fstate.gtiffUrl}>gtiff</a>`
    }

    new maplibregl.Popup()
                  .setLngLat(e.lngLat)
                  .setHTML(html)
                  .addTo(map)
})

map.on('dblclick', 'india-states-fill', (e) => {
    const sfeature = e.features[0]
    const sgeom = turf.getGeom(sfeature)
    const sbbox = turf.bbox(sgeom)
    intersecting_feature_idxs = lookupIndex.search(...sbbox)
    console.log(intersecting_feature_idxs)
    available = []
    unavailable = []
    not_downloaded = []
    for (const i of intersecting_feature_idxs) {
        const feature = indexMap[i]
        const intersects = turf.booleanIntersects(turf.getGeom(feature), sgeom)
        if (!intersects) {
            continue
        }
        const sheetNo = feature.properties.EVEREST_SH
        console.log(i, sheetNo)
        const fstate = map.getFeatureState({ id: feature.id, source: 'tiles'})
        if (!('status' in fstate)) {
            not_downloaded.push(feature)
        } else if (fstate.status !== 'not_found') {
            available.push([feature, fstate.url])
        } else {
            unavailable.push(feature)
        }
    }
        
    var html = '<table>'
    const props = sfeature.properties
    for (k in props) {
        html += `<tr><td class="td-top">${k}</td><td>${props[k]}</td></tr>`
    }

    var sheetList = ''
        
    var pieces = []
    for (const ar of available) {
        const f = ar[0]
        const url = ar[1]
        const sheetNo = f.properties.EVEREST_SH
        pieces.push(`<a target="_blank" href=${url}><b>${sheetNo}</b></a>`)
    }
    sheetList = pieces.join(' ')
    html += `<tr><td class="td-top">Available</td><td>${sheetList}</td></tr>`

    var pieces = []
    for (const f of unavailable) {
        const sheetNo = f.properties.EVEREST_SH
        pieces.push(`${sheetNo}`)
    }
    sheetList = pieces.join(' ')
    html += `<tr><td class="td-top">UnAvailable</td><td>${sheetList}</td></tr>`

    var pieces = []
    for (const f of not_downloaded) {
        const sheetNo = f.properties.EVEREST_SH
        pieces.push(`${sheetNo}`)
    }
    sheetList = pieces.join(' ')
    html += `<tr><td class="td-top">NotDownloaded</td><td>${sheetList}</td></tr>`

    html += '</table>'

    new maplibregl.Popup()
                  .setLngLat(e.lngLat)
                  .setHTML(html)
                  .addTo(map)
})

map.on('mouseenter', 'tiles-fill', () => {
    map.getCanvas().style.cursor = 'pointer'
})

map.on('mouseleave', 'tiles-fill', () => {
    map.getCanvas().style.cursor = ''
})
