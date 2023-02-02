
BOUNDS_INDIA = [[61.1113787, 2.5546079], [101.395561, 39.6745457]]
STATES_URL = 'https://storage.googleapis.com/soi_data/states.pmtiles'
INDEX_URL = 'https://storage.googleapis.com/soi_data/index.pmtiles'
const green = 'green'
const red = 'red'
const yellow = 'yellow'



let protocol = new pmtiles.Protocol()
maplibregl.addProtocol("pmtiles", protocol.tile)
const p_states = new pmtiles.PMTiles(STATES_URL)
const p_index = new pmtiles.PMTiles(INDEX_URL)
protocol.add(p_states)
protocol.add(p_index)

var map = null

p_states.getHeader().then(h => {

    map = new maplibregl.Map({
        container: 'map', 
        zoom: h.maxZoom - 3,
        maxZoom: h.maxZoom,
        /*center: [h.centerLon, h.centerLat],*/
        bounds: BOUNDS_INDIA,
        maxBounds: BOUNDS_INDIA,
        minZoom: 1,
        style:  {
            version: 8,
            sources: {
                "india-states": {
                    type: "vector",
                    url: "pmtiles://" + STATES_URL,
                },
                "tiles": {
                    type: "vector",
                    url: "pmtiles://" + INDEX_URL,
                }
            },
            layers: [
                {
                    id: 'background',
                    type: 'background',
                    paint: { 'background-color': 'black' }
                },
                {
                    id: 'tiles-fill',
                    type: 'fill',
                    'source': 'tiles', 
                    'source-layer': 'indexfgb', 
                    layout: {},
                    paint: {
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
                },
                {
                    id: 'tiles-outline',
                    type: 'line',
                    'source': 'tiles', 
                    'source-layer': 'indexfgb',
                    layout: {},
                    paint: {
                        'line-color': '#000',
                        'line-width': 0.5
                    }
                },
                {
                    id: 'india-states-fill',
                    type: 'fill',
                    'source': 'india-states',
                    'source-layer': 'statesfgb',
                    layout: {},
                    paint: {
                        'fill-color': '#000',
                        'fill-opacity': 0.0
                    }
                },
                {
                    id: 'india-states-outline',
                    type: 'line',
                    'source': 'india-states',
                    'source-layer': 'statesfgb',
                    layout: {},
                    paint: {
                        'line-color': '#000',
                        'line-width': 1
                    }
                }
            ]
        }
    })
    map.addControl(new maplibregl.NavigationControl())
    //map.doubleClickZoom.disable()

    map.once('idle', () => {
        const features = map.querySourceFeatures('tiles', {'sourceLayer': 'indexfgb'})
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
                                           source: 'tiles',
                                           sourceLayer: 'indexfgb' })
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
            const fstate = map.getFeatureState({ id: feature.id, source: 'tiles', sourceLayer: 'indexfgb'})
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
})




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
            { source: 'tiles', id: featureId, sourceLayer: 'indexfgb' },
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

function setStatus(msg, isErr) {
    var statusDiv = document.getElementById('call_status')
    var toSet = "";
    if (isErr) {
        statusDiv.style.color = 'red'
        toSet = "Error: "
    }
    toSet += msg
    statusDiv.innerHTML = msg
}

function fetchStatusInfoCb(err, data) {
    if (err !== null) {
        console.log(err)
        setStatus("Couldn't get status list", true)
    } else {
        setStatus('', false)
        updateStatusInfo(data)
    }
}


window.onload = (event) => {
    setStatus('Loading Status Info..', false)
    getStatusData(fetchStatusInfoCb)
}


