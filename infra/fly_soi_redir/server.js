const fetch = require('node-fetch');
const fastify = require('fastify')({ logger: true });
const pmtiles = require('pmtiles');
const tilebelt = require('@mapbox/tilebelt');

const url = 'https://github.com/ramSeraph/opendata/releases/download/soi-latest/mosaic.json';
const ancillaryUrl = 'https://github.com/ramSeraph/opendata/releases/download/soi-ancillary/';
const port = 3000;

let pmtilesDict = null;
let mimeTypes = null;

function _getBounds(coord) {
  const b = tilebelt.tileToBBOX([coord.x, coord.y, coord.z]);
  const w = b[0], s = b[1], e = b[2], n = b[3];
  return [[s, w], [n, e]];
}

function _isInSource(header, bounds) {
  const corner0 = bounds[0];
  const corner1 = bounds[1];
  if (corner0[0] > header['maxLat'] ||
      corner0[1] > header['maxLon'] ||
      corner1[0] < header['minLat'] ||
      corner1[1] < header['minLon']) {
      return false;
  }
  return true;
}

function getSourceKey(coord) {
  let z = coord.z;
  let k = null;
  const bounds = _getBounds(coord);
  for (const [key, entry] of Object.entries(this.dict)) {
    if (z > entry.header.max_zoom || z < entry.header.min_zoom) {
      continue;
    }
    if (!_isInSource(entry.header, bounds)) {
      continue;
    }
    k = key;
    fastify.log.info(`key=${k} for  (${coord.x} ${coord.y} ${coord.z})`);
    break;
  }
  return k;
}

function getSource(key) {
  return pmtilesDict[key].pmtiles;
}

function _resolveKey(key) {
  if (key.startsWith('../')) {
    return url + '/' + key;
  }
  return key;
}

function getMimeType(t) {
  if (t == pmtiles.TileType.Png) {
    return "image/png";
  } else if (t == pmtiles.TileType.Jpeg) {
    return "image/jpeg";
  } else if (t == pmtiles.TileType.Webp) {
    return "image/webp";
  } else if (t == pmtiles.TileType.Avif) {
    return "image/avif";
  }
  throw Error(`Unknown tiletype ${t}`);
}

async function populateMosaic() {
  let res = await fetch(url);
  let data = await res.json();
  pmtilesDict = {};
  mimeTypes = {};
  for (const [key, entry] of Object.entries(data)) {
    var header = entry.header;
    var resolvedUrl = _resolveKey(key);
    var archive = new pmtiles.PMTiles(resolvedUrl);
    header['minLat'] = header['min_lat_e7'] / 10000000;
    header['minLon'] = header['min_lon_e7'] / 10000000;
    header['maxLat'] = header['max_lat_e7'] / 10000000;
    header['maxLon'] = header['max_lon_e7'] / 10000000;
    pmtilesDict[key] = { 'pmtiles': archive, 'header': header };
    mimeTypes[key] = getMimeType(header.tile_type);
  }
  fastify.log.info(pmtilesDict);
}

async function getTile(request, reply) {
  const { z, x, y } = request.params;
  let k = null;
  let bounds = _getBounds(request.params);
  for (const [key, entry] of Object.entries(pmtilesDict)) {
    if (z > entry.header.max_zoom || z < entry.header.min_zoom) {
      continue;
    }
    if (!_isInSource(entry.header, bounds)) {
      continue;
    }
    k = key;
    fastify.log.info(`found key=${k} for (${x} ${y} ${z})`);
    break;
  }
  if (k === null) {
    return reply.code(404).send('');
  }
  let source = getSource(k);
  let arr = await source.getZxy(z,x,y);
  if (arr) {
    return reply.header('Content-Type', mimeTypes[k])
                .header('Cache-Control', 'max-age=86400')
                .send(new Uint8Array(arr.data));
  }
  return reply.code(404).send('');
}

function getCorsProxyFn(targetUrl, request, reply) {
    return async function(request, reply) {
      const tResp = await fetch(targetUrl)
      const stream = tResp.body;
      return reply.header("Access-Control-Allow-Origin", "*")
                  .send(stream);
    }
}


async function start() {
  try {
    fastify.addHook('onReady', populateMosaic);
    fastify.get('/export/tiles/:z/:x/:y.webp', getTile);
    fastify.get('/index.geojson', getCorsProxyFn(ancillaryUrl + 'index.geojson'));
    fastify.get('/polymap15m_area.geojson', getCorsProxyFn(ancillaryUrl + 'polymap15m_area.geojson'));
    await fastify.listen({ host: '0.0.0.0', port: port });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

start();
