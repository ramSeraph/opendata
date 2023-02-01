// used to create turf.min.js not to be served directly
var bbox = require('@turf/bbox')
var booleanIntersects = require('@turf/boolean-intersects')
module.exports = {
    ...require('@turf/invariant'),
    bbox: bbox.default,
    booleanIntersects: booleanIntersects.default
};
