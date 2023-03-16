
// TODO: move to pmtiles
// TODO: highlight sheet on hover
//
// unlikely to be fixed
// TODO: legend/popup should block click events.. 
// TODO: adjust viewport on fullscreen.. show what was being shown before

INDEX_URL = 'https://storage.googleapis.com/soi_data/index.geojson';
// STATES_URL = 'https://raw.githubusercontent.com/datameet/maps/master/website/docs/data/geojson/states.geojson';

function makeLink(url, text) {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`;
}

INDEX_ATTRIBUTION = makeLink("https://onlinemaps.surveyofindia.gov.in/FreeOtherMaps.aspx", "SOI OSM Index(simplified)");
// STATES_ATTRIBUTION = makeLink("https://github.com/datameet/maps/blob/master/website/docs/data/geojson/states.geojson", "Datameet State boundaries");


// copied from openlayers code
function getElementSize(el) {
    const computedStyle = getComputedStyle(el);
    const width =
        el.offsetWidth -
        parseFloat(computedStyle['borderLeftWidth']) -
        parseFloat(computedStyle['paddingLeft']) -
        parseFloat(computedStyle['paddingRight']) -
        parseFloat(computedStyle['borderRightWidth']);
    const height =
        el.offsetHeight -
        parseFloat(computedStyle['borderTopWidth']) -
        parseFloat(computedStyle['paddingTop']) -
        parseFloat(computedStyle['paddingBottom']) -
        parseFloat(computedStyle['borderBottomWidth']);
    return [width, height];
}

function updateMap(map, extent) {
    const eCenter = ol.extent.getCenter(extent);
    const eSize = ol.extent.getSize(extent);
    console.log('extent size', eSize);

    // update map div size 
    let el = map.getTargetElement();
    const tSize = getElementSize(el);
    console.log('target size', tSize);
    const expectedHeight = Math.ceil(eSize[1] * (tSize[0]/eSize[0]));
    el.style.height = `${expectedHeight}px`;
    console.log(`setting container height to ${expectedHeight}`);
    map.updateSize();

    let view = map.getView();
    const size = map.getSize();
    const resolution = view.getResolutionForExtent(extent, size);
    console.log('resolution', resolution);
    const zoom = view.getZoomForResolution(resolution);
    const intZoom = Math.floor(zoom);
    view.setZoom(intZoom);
    view.setMinZoom(intZoom);
    view.setCenter(eCenter);
    view.fit(extent);
}

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

function getTilePopoverContent(sheetNo, statusMap) {
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
    //TODO: add link to demo map
    return html;
}


function getStyleFn(statusMap) {
    return (f) => {
        const sheetNo = f.get('EVEREST_SH');
        const sheetInfo = statusMap[sheetNo];
        if (sheetInfo === undefined) {
            baseStyle.getStroke().setColor('grey');
            baseStyle.getFill().setColor('rgba(255,255,255,0.0)');
        } else {
            const status = sheetInfo['status'];
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
        }
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
            'Not Parsable':  { 'status': 'found' }
        })
    });
    const legendSymbolPoints = [[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]];
    for (let s of ['Available', 'Not Available', 'Not Parsable', 'Info Unavailable']) {
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

function getControls() {
    let controls = ol.control.defaults.defaults();
    let fControl = new ol.control.FullScreen();

    /*

    // NOTE: didn't work
    var adjustToPrevState = (e) => {
        console.log(e);
        const map = e.target.getMap();
        if (!map) {
            return;
        }
        let view = map.getView();
        let { viewState, extent } = view.getViewStateAndExtent();
        view.fit(extent);
    };
    fControl.on('enterfullscreen', adjustToPrevState);
    fControl.on('leavefullscreen', adjustToPrevState);

    */
    controls.push(fControl);
    return controls;
}

function getInteractions() {
    let interactions = ol.interaction.defaults.defaults();
    let pinchIndex = -1;
    for (let i = 0; i < interactions.getLength(); i++) {
        if (interactions.item(i) instanceof ol.interaction.PinchRotate) {
            pinchIndex = i;
            break;
        }
    }
    if (pinchIndex !== -1) {
        interactions.removeAt(pinchIndex);
    }

    return interactions;
}

function getDocStyle(el) {
    const style = getComputedStyle(el);
    const fontFamily = style['fontFamily'];
    const fontSize = style['fontSize'];
    const lineHeight = style['lineHeight'];
    const color = style['color'];
    const backgroundColor = style['backgroundColor'];
    return { fontFamily, fontSize, lineHeight, color, backgroundColor };
}

function getTextStyle(el) {
    let { fontFamily, fontSize, lineHeight, color, backgroundColor } = getDocStyle(el);
    const olTextStyle  = new ol.style.Text({
      font: `${fontSize}/${lineHeight} ${fontFamily}`,
      fill: new ol.style.Fill({
        color: color
      }),
      backgroundFill: new ol.style.Fill({
        color: backgroundColor
      })
    });
    return olTextStyle;
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
            updateMap(map, src.getExtent());
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
            return getTilePopoverContent(sheetNo, sheetStatusMap);
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

    /*
    map.on('click', function (e) {
        console.log(e);
        const features = map.getFeaturesAtPixel(e.pixel);
        console.log(features)
        const feature = features.length ? features[0] : undefined;
        if (feature === undefined) {
            popup.hide();
            return;
        }
        const html = getTilePopoverContent(feature, sheetStatusMap);
        popup.show(e.coordinate, html);
    });
    map.on('pointermove', function (e) {
        // const hasFeature = map.hasFeatureAtPixel(e.pixel, function(layer) {
        // });
        const features = map.getFeaturesAtPixel(e.pixel);
        // const type = map.hasFeatureAtPixel(e.pixel) ? 'pointer' : 'inherit';
        // map.getViewport().style.cursor = type;
        console.log(features)
        const feature = features.length ? features[0] : undefined;
        if (feature === undefined) {
            popup.hide();
            return;
        }
        const html = getTilePopoverContent(feature, sheetStatusMap);
        popup.show(e.coordinate, html);

    });
    */
    // updateMap(map);
    // map.addInteraction(new ol.interaction.Link());
});
