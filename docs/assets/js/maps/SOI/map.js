
// TODO: move to pmtiles
// TODO: highlight sheet on hover
//
// unlikely to be fixed
// TODO: legend/popup should block click events.. 
// TODO: adjust viewport on fullscreen.. show what was being shown before

INDEX_URL = '../osm_index.geojson';
// STATES_URL = 'https://raw.githubusercontent.com/datameet/maps/master/website/docs/data/geojson/states.geojson';

INDEX_ATTRIBUTION = makeLink("https://onlinemaps.surveyofindia.gov.in/FreeOtherMaps.aspx", "SOI OSM Index(simplified)");
// STATES_ATTRIBUTION = makeLink("https://github.com/datameet/maps/blob/master/website/docs/data/geojson/states.geojson", "Datameet State boundaries");

const baseStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({
        color: 'black',
        width: 0.5,
    }),
    fill: new ol.style.Fill({
        color: 'rgba(255,255,255,0.9)',
    }),
});

const statesStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({
        color: 'white',
        width: 2,
    }),
    fill: new ol.style.Fill({
        color: 'rgba(255,255,255,0.0)',
    }),
});


const parsed_color = '#f4f4f4';
const found_color = '#b3b3b3';
const not_found_color = '#5e5e5e';

function getTilePopoverContent(sheetNo, feature, statusMap) {
    const sheetInfo = statusMap[sheetNo];

    var html = `<b text-align="center">${sheetNo}</b><br>`
    if (sheetInfo === undefined) {
        return html;
    }
    if ('pdfUrl' in sheetInfo && sheetInfo['pdfUrl'] !== null) {
        html += ' ';
        html += `<a target="_blank" href=${sheetInfo['pdfUrl']}>pdf</a>`;
    }
    if ('gtiffUrl' in sheetInfo && sheetInfo['gtiffUrl'] !== null) {
        html += ' ';
        html += `<a target="_blank" href=${sheetInfo['gtiffUrl']}>gtiff</a>`;
    }

    const extent = feature.getGeometry().getExtent();
    const cx = (extent[0] + extent[2]) / 2;
    const cy = (extent[1] + extent[3]) / 2;
    html += ' ';
    html += `<a target="_blank" href=compare?x=${cx}&y=${cy}&z=11&r=0&l=10000111$>view</a>`;
    return html;
}


function getStyleFn(statusMap) {
    return (f) => {
        const sheetNo = f.get('EVEREST_SH');
        const sheetInfo = statusMap[sheetNo];
        const status = ( sheetInfo === undefined ) ? 'not_found' : sheetInfo['status'];
        baseStyle.getStroke().setColor('black');
        var color;
        if (status === 'not_found') {
            color = not_found_color;
        } else if (status === 'found') {
            color = found_color;
        } else if (status === 'parsed') {
            color = parsed_color;
        }
        baseStyle.getFill().setColor(color);
        return baseStyle;
    };
}

function getLegendCtrl(textStyle) {

    var legend = new ol.legend.Legend({
        'title': 'Legend',
        'size': [15, 15],
        // 'maxWidth':     
        'margin': 5,
        'textStyle': textStyle,
        'style': getStyleFn({
            'Available':     { 'status': 'parsed' },
            'Not Available': { 'status': 'not_found' },
            'Not Parsed':    { 'status': 'found' }
        })
    });
    const legendSymbolPoints = [[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]];
    for (let s of ['Available', 'Not Available', 'Not Parsed']) {
        legend.addItem(new ol.legend.Item({
            'title': s,
            'textStyle': textStyle,
            'feature': new ol.Feature({
                'EVEREST_SH': s,
                'geometry': new ol.geom.Polygon(legendSymbolPoints)
            }),
        }));
    }
    legend.on('select', (e) => {
        console.log(e);
    });
    const legendCtrl = new ol.control.Legend({
        legend: legend,
        collapsed: true
    });

    return legendCtrl;
}


document.addEventListener("DOMContentLoaded", () => {

    var successCount = 0;
    // 2 status updates for each layer, 2 for the map, 1 for the sheeet list map
    // var expectedSuccessCount = 7;
    var expectedSuccessCount = 5;
    var statusElem = document.getElementById('call_status');
    var setStatus = (msg, err) => {
        var alreadyError = false;
        const prevMsg = statusElem.innerHTML;
        if (statusElem.hasAttribute("class")) {
            alreadyError = true;
        }
        if (err === true) {
            if (alreadyError === true) {
                msg = prevMsg + '<br>' + msg;
            } else {
                statusElem.setAttribute("class", "error");
            }
            statusElem.innerHTML = msg;
        } else if (alreadyError !== true) {
            statusElem.removeAttribute("class");
            successCount += 1;
            if (expectedSuccessCount <= successCount) {
                msg = '';
            }
            statusElem.innerHTML = msg;
        }
    };

    var sheetStatusMap = {}
    getStatusData((err, data) => {
        if (err !== null) {
            console.log(err);
            setStatus("Failed to get status list", true);
        } else {
            Object.assign(sheetStatusMap, data);
            setStatus('Done loading status list', false);
        }
    });

    ol.proj.useGeographic();

    const map = new ol.Map({
        interactions: getInteractions(),
        controls: getControls(),
        target: 'map',
        view:  new ol.View({
            // extent: 
            showFullExtent: true,
            maxZoom: 9,
            center: [0, 0],
            zoom: 2,
        })
    });

    var mapElem = document.getElementById('map');

    var createLayer = (url, srcLabel, attribution, style, statusFn) => {
    
        const src = new ol.source.Vector({
            format: new ol.format.GeoJSON(),
            url: url,
            overlaps: false,
            attributions: [ attribution ]
        });
        const layer = new ol.layer.Vector({
            background: 'black',
            source: src,
            style: style
        });
    
        src.on('featuresloadstart', (e) => {
            statusFn(`Loading ${srcLabel} features..`, false);
        });
        src.on('featuresloadend', (e) => {
            console.log(e);
            statusFn(`Done loading ${srcLabel} features`, false);
            updateMap(map, mapElem, src.getExtent());
        });
        src.on('featuresloaderror', (e) => {
            statusFn(`Failed to load ${srcLabel}`, true);
        });
        return layer;
    };

    const indexLayer = createLayer(INDEX_URL, 'Index', INDEX_ATTRIBUTION, getStyleFn(sheetStatusMap), setStatus);
    map.addLayer(indexLayer);

    // const statesLayer = createLayer(STATES_URL, 'State Boundaries', STATES_ATTRIBUTION, statesStyle, setStatus);
    // map.addLayer(statesLayer);


    function showPopup(e, pop, contentFn) {
        const features = map.getFeaturesAtPixel(e.pixel);
        const feature = features.length ? features[0] : undefined;
        if (feature === undefined) {
            pop.hide();
            return;
        }
        const html = contentFn(feature);
        if (html === null) {
            pop.hide();
            return;
        }
        pop.show(e.coordinate, html);
    }

    var popup = new ol.Overlay.Popup({
        popupClass: "tooltips black", //"tooltips", "warning" "black" "default", "tips", "shadow",
        closeBox: false,
        positioning: 'center-left',
        autoPan: {
          animation: { duration: 250 }
        }
    });
    map.addOverlay(popup);
    var tooltip = new ol.Overlay.Popup({
        popupClass: "tooltips black", //"tooltips", "warning" "black" "default", "tips", "shadow",
        closeBox: false,
        positioning: 'center-left',
        autoPan: {
          animation: { duration: 250 }
        }
    });

    let activePopupSheetNo = null;
    let activeTooltipSheetNo = null;
    map.addOverlay(tooltip);
    map.on('click', function(e) {
        showPopup(e, popup, (f) => {
            const sheetNo = f.get('EVEREST_SH');
            if (tooltip.getVisible() && sheetNo === activeTooltipSheetNo) {
                tooltip.hide();
            }
            activePopupSheetNo = sheetNo;
            return getTilePopoverContent(sheetNo, f, sheetStatusMap);
        });
    });
    map.on('pointermove', function(e) {
        showPopup(e, tooltip, (f) => {
            const sheetNo = f.get('EVEREST_SH');
            if (popup.getVisible() && sheetNo === activePopupSheetNo) {
                return null;
            }
            activeTooltipSheetNo = sheetNo;
            return `<b text-align="center">${sheetNo}</b>`;
        });
    });

    map.addControl(getLegendCtrl(getTextStyle(document.body)));
    map.on('loadstart', function () {
        setStatus('Loading Map..', false);
    });
    map.on('loadend', function () {
        setStatus('Done loading Map', false);
    });

});

