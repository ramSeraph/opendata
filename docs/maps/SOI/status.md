---
layout: page
title: SOI Extraction Status
permalink: /maps/SOI/status
---


<script src='https://unpkg.com/maplibre-gl@1.15.2/dist/maplibre-gl.js'></script>
<script src="https://unpkg.com/pmtiles@2.7.0/dist/index.js"></script>
<script src="https://cdn.jsdelivr.net/npm/flatbush"></script>
<link rel="stylesheet" property="stylesheet" type="text/css" href='https://unpkg.com/maplibre-gl@1.15.2/dist/maplibre-gl.css' />
<link rel="stylesheet" property="stylesheet" type="text/css" href="{{ "/assets/css/maps/SOI/map.css" | relative_url }}">

<div id='call_status'></div>
<div id="map"></div>
<hr>
<ul>
  <li>Legend
    <ul>
        <li class="green-text">Green:  Data Avaialble</li>
        <li class="yellow-text">Yellow: Data Avaialble but not parsable</li>
        <li class="red-text">Red:    No Data Avaialble</li>
    </ul>
  </li>
</ul>
<ul>
  <li>Sources
    <ul>
      <li><a href="https://github.com/datameet/maps/blob/master/website/docs/data/geojson/states.geojson">Datameet State boundaries</a></li>
      <li><a href="https://onlinemaps.surveyofindia.gov.in/FreeOtherMaps.aspx">Survey of India Open Series Map Index( simplified by me )</a></li>
    </ul>
  </li>
</ul>
<script src="{{ "/assets/js/maps/SOI/turf.min.js" | relative_url }}" ></script>
<script src="{{ "/assets/js/maps/SOI/sheets_common.js" | relative_url }}" ></script>
<script src="{{ "/assets/js/maps/SOI/map.js" | relative_url }}" ></script>
