---
layout: page
title: SOI Extraction Status
permalink: /maps/SOI/status
custom-js-list:
  - url: "https://unpkg.com/protomaps@1.9.3/p ist/protomaps.min.js"
    rel: false
  - url: "https://unpkg.com/protomaps@1.23.0/dist/protomaps.min.js"
    rel: false
  - url: "https://cdn.jsdelivr.net/npm/flatbush"
    rel: false
  - url: "/assets/js/maps/SOI/turf.min.js"
  - url: "/assets/js/maps/SOI/sheets_common.js"
  - url: "/assets/js/maps/SOI/map.js"
custom-css-list:
  - url: "/assets/css/maps/SOI/common.css" 
  - url: "/assets/css/maps/SOI/map.css"
---

<div id='call_status'>Loading Page..</div>
<div id="map"></div>

---
Legend
: - <span class="green-text">Data Available</span>
  - <span class="yellow-text">Data Available but not parsable</span>
  - <span class="red-text">Data Unavailable</span>
---
Sources
: - (https://github.com/datameet/maps/blob/master/website/docs/data/geojson/states.geojson)[Datameet State boundaries]
  - (https://onlinemaps.surveyofindia.gov.in/FreeOtherMaps.aspx)[Survey of India Open Series Map Index( simplified by me )]
