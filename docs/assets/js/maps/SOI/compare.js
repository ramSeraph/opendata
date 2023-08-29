
const GRID_LAYER_INDEX = 'SOI OSM Index Grid';

const boundaryStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({
        color: 'black',
        width: 2,
    }),
    fill: new ol.style.Fill({
        color: 'rgba(255,255,255,0.0)',
    }),
});

const gridStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({
        color: 'black',
        width: 1,
    }),
    fill: new ol.style.Fill({
        color: 'rgba(255,255,255,0.0)',
    }),
});

function getMap(target, layers) {
    return new ol.Map({
        controls: [],
        interactions: getInteractions(),
        target: target,
        view: new ol.View({
            zoom: 2,
            maxZoom: 14,
            center: [0, 0]
        }),
    });
}

const soi_attribution = makeLink('https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx', '1:50000 Open Series Maps') +
                    ' &copy; ' +
                    makeLink('https://www.surveyofindia.gov.in/pages/copyright-policy', 'Survey Of India');
function getSOILayer() {
    const src = new ol.source.XYZ({
        url: 'https://soi.fly.dev/export/tiles/{z}/{x}/{y}.webp',
        attributions: [soi_attribution],
    });
    return new ol.layer.Tile({
        background: 'grey',
        source: src,
        maxZoom: 14,
    });
}

function getGridSource() {
    const src = new ol.source.Vector({
        format: new ol.format.GeoJSON(),
        url: 'https://soi.fly.dev/index.geojson',
        overlaps: false,
        attributions: [
            makeLink("https://onlinemaps.surveyofindia.gov.in/FreeOtherMaps.aspx", "SOI OSM Index(simplified)")
        ]
    });
    return src;
}

function getIndiaOutlineSource(map1, map2, container, statusFn) {
    const url = 'https://soi.fly.dev/polymap15m_area.geojson';
    const src = new ol.source.Vector({
        format: new ol.format.GeoJSON(),
        url: url,
        overlaps: false,
        attributions: [
            makeLink("https://surveyofindia.gov.in/pages/outline-maps-of-india", "SOI India Outline")
        ]
    });

    const srcLabel = 'India Outline';
 
    src.on('featuresloadstart', (e) => {
        statusFn(`Loading ${srcLabel} features..`, false);
    });
    src.on('featuresloadend', (e) => {
        statusFn(``, false);
        updateMap(map1, container, src.getExtent());
        updateMap(map2, container, src.getExtent());
    });
    src.on('featuresloaderror', (e) => {
        statusFn(`Failed to load ${srcLabel}`, true);
    });
    return src;
}


function getLayer(src, style, visible) {
    const layer = new ol.layer.Vector({
        visible: visible,
        source: src,
        style: gridStyle
    });
    return layer;
}


function getLayerGroup() {

    const osmLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({
            url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', 
            attributions: [
                '&copy; ' + makeLink('https://www.openstreetmap.org/copyright', 'OpenStreetMap contributors') 
            ],
        }),
        baseLayer: true,
        visible: true,
        maxZoom: 19,
        title: 'OpenStreetMap',
    });
    const gStreetsLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({
            url: 'https://mt{0-3}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attributions: [
                'Map data &copy; 2023 Google'
            ]
        }),
        baseLayer: true,
        visible: false,
        maxZoom: 20,
        title: 'Google Streets',
    });
    const gHybridLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({
            url: 'https://mt{0-3}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}',
            attributions: [
                'Map data &copy; 2023 Google',
                'Imagery &copy; 2023 TerraMetrics'
            ]
        }),
        baseLayer: true,
        visible: false,
        maxZoom: 20,
        title: 'Google Hybrid',
    });
    const esriWorldLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attributions: [
                'Tiles &copy; Esri',
                'Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, ' +
                'Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
            ]
        }),
        baseLayer: true,
        visible: false,
        maxZoom: 20,
        title: 'ESRI Satellite',
    });
    const otmLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({
            url: 'https://{a-c}.tile.opentopomap.org/{z}/{x}/{y}.png', 
            attributions: [
                'Map data: &copy; ' + makeLink('https://www.openstreetmap.org/copyright', 'OpenStreetMap contributors'),
                makeLink('http://viewfinderpanoramas.org', 'SRTM'),
                'Map style: &copy; ' +
                makeLink('https://opentopomap.org', 'OpenTopoMap') +
                ' (' + makeLink('https://creativecommons.org/licenses/by-sa/3.0/', 'CC-BY-SA') + ')'
            ]
        }),
        baseLayer: true,
        visible: false,
        maxZoom: 17,
        title: 'OpenTopoMap'
    });

    return new ol.layer.Group({
        title: 'Base Layers',
        openInLayerSwitcher: true,
        layers: [
            gHybridLayer,
            gStreetsLayer,
            esriWorldLayer,
            otmLayer,
            osmLayer,
        ]
    });
}

document.addEventListener("DOMContentLoaded", () => {

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
            statusElem.innerHTML = msg;
        }
    };

    ol.proj.useGeographic();

    var map1 = getMap('map1');
    var map2 = getMap('map2');

    const soiLayer = getSOILayer();
    map1.addLayer(soiLayer);
    map2.addLayer(new ol.layer.Vector({
        source: new ol.source.Vector({
            attributions: [soi_attribution]
        })}
    ));
    const layerGroup = getLayerGroup();
    map2.addLayer(layerGroup);

    var compareElem = document.getElementById('compare');
    var indiaOutlineSrc = getIndiaOutlineSource(map1, map2, compareElem, setStatus);
    var addOutlineLayer = (map) => {
        map.addLayer(new ol.layer.Vector({
            title: 'SOI India Outline',
            visible: true,
            source: indiaOutlineSrc,
            style: boundaryStyle,
            displayInLayerSwitcher: false
        }));
    };
    addOutlineLayer(map1);
    addOutlineLayer(map2);

    const gridSrc = getGridSource();
    var getGridLayer = () => {
        return new ol.layer.Vector({
            title: GRID_LAYER_INDEX,
            visible: false,
            source: gridSrc,
            style: gridStyle,
            displayInLayerSwitcher: true
        });
    };
    const gridLayer1 = getGridLayer();
    const gridLayer2 = getGridLayer();
    map1.addLayer(gridLayer1);
    map2.addLayer(gridLayer2);

    function showPopup(map, e, pop, contentFn) {
        var features = map.getFeaturesAtPixel(e.pixel);
        features = features.filter((f) => f.get('EVEREST_SH'));
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

    function addPopup(layer, map) {
      var popup = new ol.Overlay.Popup({
        popupClass: "default", //"tooltips", "warning" "black" "default", "tips", "shadow",
        closeBox: true,
        positioning: 'center-left',
        autoPan: {
          animation: { duration: 250 }
        }
      });
      map.addOverlay(popup);
      map.on('click', function(e) {
        if (!layer.getVisible()) {
            return;
        }
        showPopup(map, e, popup, (f) => {
            const sheetNo = f.get('EVEREST_SH');
            return '<b text-align="center">' + sheetNo + '</b>';
        });
      });

      return popup;
    }

    addPopup(gridLayer2, map2);

    var swipe = new ol.control.SwipeMap({ right: true });

    function tickleSwipe() {
      const pos = swipe.get('position');
      console.log('tickle', pos);
      swipe.set('position', pos - 0.000001);
    }
    map2.on('change:size', function(e) {
        // hack to trigger redraw on fullscreen and inital render
        console.log('change event fired:', e);
        tickleSwipe();
    });


    map1.addInteraction(new ol.interaction.Synchronize({ maps: [map2] }));
    map2.addInteraction(new ol.interaction.Synchronize({ maps: [map1] }));
    var layerSwitcher = new ol.control.LayerSwitcher({
        reordering: false,
        noScroll: true,
        mouseover: true,
    });
    layerSwitcher.on('layer:visible', (e) => {
        // console.log('layer:visible', e);
        const l = e.layer;
        if (l.get('title') === GRID_LAYER_INDEX) {
            gridLayer1.setVisible(l.getVisible());
        }
    });
    // layerSwitcher.on('select', (e) => {
    //    console.log(e);
    // });
    map2.addControl(layerSwitcher);

    map2.addControl(new ol.control.FullScreen({ source: 'compare' }));
    map2.addControl(new ol.control.Zoom());
    map2.addControl(new ol.control.Attribution({ collapsed: true, collapsible: true }));
    // map1.addControl(new ol.control.Attribution({ collapsed: true, collapsible: true}));
    var currentMode;
    function setMode(mode) {
        if (mode) {
            currentMode = mode;
            // Remove tools
            map2.removeControl(swipe);
            // Set interactions
            switch (mode) {
                case 'swipev':
                case 'swipeh': {
                    map2.addControl(swipe);
                    swipe.set('orientation', (mode==='swipev' ? 'vertical' : 'horizontal'));
                    break;
                }
            }
            // Update position
            document.getElementById("compare").className = mode;
        }
        map1.updateSize();
        map2.updateSize();
    }
    setMode('swipev');
});
