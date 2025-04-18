---
layout: page
title: SOI
permalink: /maps/SOI/
---

Collection of Open Series Maps from [Survey Of India](https://onlinemaps.surveyofindia.gov.in) -  [Copyright Notice](https://surveyofindia.gov.in/pages/copyright-policy)

[Code](https://github.com/ramSeraph/opendata/tree/master/maps/SOI) used to extract this data.

All the data below is updated monthly

# Collection Summary
* [List Of All Available Sheets](sheets)
* [Extraction Status Page](status)

# Get A Copy
The data is also hosted as a mosaic of [pmtiles](https://protomaps.com/docs/pmtiles) files in the [releases](https://github.com/ramSeraph/opendata/releases/tag/soi-latest)


This can be downloaded as local [mbtiles](https://docs.mapbox.com/help/glossary/mbtiles/) by running the following commands( after installing [uv](https://docs.astral.sh/uv/getting-started/installation/):


```
uv run https://raw.githubusercontent.com/ramSeraph/indianopenmaps/refs/heads/main/utils/download_as_mbtiles.py https://github.com/ramSeraph/opendata/releases/download/soi-latest/soi.mosaic.json soi.mbtiles

```


This creates a file `soi.mbtiles` in the current directory containing the whole data.

The process requires a disk space of around 12GB and will download around 10GB from the internet.

# Web
* Tile URL
  * `https://indianopenmaps.fly.dev/soi/osm/{z}/{x}/{y}.webp`
* Demo Page
  * [DEMO of the tilemap](compare)

# JOSM
* Plugins needed to use the above tile url with JOSM
  * ImageIO plugin
    * After enabling the plugin enable webp in Imagery Preferences -> ImageIO tab
* A locally downloaded `soi.mbtiles` file can also be used by installing the following plugins and opening the file in JOSM.
  * ImageIO plugin
    * After enabling the plugin enable webp in Imagery Preferences -> ImageIO tab
  * [iandees/josm-mbtiles](https://github.com/iandees/josm-mbtiles)

# Appendix
* [Notes](notes) on the what was done to get the data in the present form and possible problems.
* [Original sheet grid shapefile](https://github.com/ramSeraph/opendata/releases/download/soi-ancillary/OSM_SHEET_INDEX.zip)
* [Modified Index geojson for the sheet grid](https://github.com/ramSeraph/opendata/releases/download/soi-ancillary/index.geojson)
