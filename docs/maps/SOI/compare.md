---
layout: page
title: SOI Demo Page
menu_title: Demo
permalink: /maps/SOI/compare
parent: /maps/SOI/
custom-js-list:
  - url: "https://cdn.jsdelivr.net/npm/elm-pep@1.0.6/dist/elm-pep.js"
    abs: true
  - url: "https://cdn.jsdelivr.net/npm/ol@v7.3.0/dist/ol.js"
    abs: true
  - url: "https://cdn.jsdelivr.net/gh/Viglino/ol-ext@v4.0.5/dist/ol-ext.min.js"
    abs: true
  - url: "/assets/js/maps/SOI/sheets_common.js"
  - url: "/assets/js/maps/SOI/ol_common.js"
  - url: "/assets/js/maps/SOI/compare.js"
custom-css-list:
  - url: "https://cdn.jsdelivr.net/npm/ol@v7.3.0/ol.css"
    abs: true
  - url: "https://cdn.jsdelivr.net/gh/Viglino/ol-ext@v4.0.5/dist/ol-ext.min.css"
    abs: true
  - url: "https://viglino.github.io/font-gis/css/font-gis.css"
    abs: true
  - url: "/assets/css/maps/SOI/compare.css"
---
# Compare Maps

<div id='call_status'></div>
<div id="compare" class="compare">
   <div id="map1"></div>
   <div id="map2"></div>
</div>
