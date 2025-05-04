
const DEFAULT_PADDING = Array(4).fill(50);

function makeLink(url, text) {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`;
}

function hasUrlParams() {
    const url = new URL(window.location.href);
    const params = url.searchParams;
    // console.log("url_params", params);
    const keysForLink = [ 'x', 'y', 'z', 'r', 'l' ];
    for (const k of keysForLink) {
        if (params.has(k)) {
            return true;
        }
    }
    return false;
}

const areUrlParamsAlreadySet = hasUrlParams();

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

function updateMap(map, el, extent) {
    const eCenter = ol.extent.getCenter(extent);
    const eSize = ol.extent.getSize(extent);

    // update map div size 
    const tSize = getElementSize(el);
    const expectedHeight = Math.ceil(eSize[1] * (tSize[0]/eSize[0]));
    el.style.height = `${expectedHeight}px`;
    map.updateSize();


    // constrain the zoom level
    let view = map.getView();
    const size = map.getSize();
    const resolution = view.getResolutionForExtent(extent, size);
    var zoom = view.getZoomForResolution(resolution);
    zoom = Math.floor(zoom);
    view.setMinZoom(zoom);

    // constrain extent as well
    let constraints = view.getConstraints();
    constraints.center = ol.View.createCenterConstraint({
        extent: ol.proj.fromUserExtent(extent, ol.proj.createProjection('EPSG:3857')),
        constrainOnlyCenter: false
    });


    if (areUrlParamsAlreadySet) {
        return;
    }

    view.setCenter(eCenter);
    view.setZoom(zoom);
    view.fit(extent, { padding: DEFAULT_PADDING });
}

function getControls() {
    let controls = ol.control.defaults.defaults();
    let fControl = new ol.control.FullScreen();
    controls.push(fControl);
    return controls;
}

function removePinchRotate(interactions) {
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
}

function getInteractions() {
    let interactions = ol.interaction.defaults.defaults();
    interactions.push(new ol.interaction.Link());
    removePinchRotate(interactions);
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


