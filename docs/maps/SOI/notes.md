---
layout: page
title: SOI collection notes
permalink: /maps/SOI/notes
---

The whole thing has been done in a way that is reproducible, starting from the source data

* Scraping
    * Logins were crowd sourced and used to download the sheets
    * Downloading was automated to overcome the pointless restrictions placed
    * After the initial run to get all the sheets, now only previously unavailable sheets are checked weekly for any newly available data


* Parsing
    * The index shape file was converted into wgs84 geojson
        * extra corrections from [index.geojson.corrections](https://github.com/ramSeraph/opendata/blob/master/maps/SOI/index.geojson.corrections) were applied
            * mostly for sheets where index was not a square or deviated too far from being a 15 minute multiple
        * coordinates in the index file were rounded off to 15 minute intervals
        * and rearranged counter clockwise starting from top left
    * Images were converted from pdf to jpegs using `mupdf`
        * Some of them did have vector information, but for the purpose of creating a tilemap it was not needed
        * Flavor is an internal catogarization of the pdfs based on the software used to produce it
            * Pure Image flavors
                * `Image PDF` - 1793
                * `Photoshop` - 21
            * Vector flavors
                * Text is also vector
                    * `Adultpdf` - 13
                    * `PDFOut` - 1326
                    * `Microstation` - 1
                * Text is easily extractable
                    * `Distiller` - 1090
                    * `Ghostscript` - 1
    * The images were too big to apply wholesale image processing techniques ( tried to avoid things running into minutes where possible )
        * So a shrunk image is first used to locate the pink collar around the map and crop the big picture
        * Couldn't locate the actual black corners on the small picture, so crop just the corners of the previously cropped big picture and use opencv to find lines
        * use the line intersections from the lines located in each of the cropped corners.. these become the map corner points
        * use the cordinates of the above corner points and geospatial coordinates from the index file to georeference the image
        * some of the sheets were not exactly squares or covered more than on sheet index, these were handled slightly differently
            * for the list of these sheets look at [known problems](https://github.com/ramSeraph/opendata/blob/master/maps/SOI/known_problems.py)
            * above link has the list of bad files which couldn't be used
        * additionally the grid lines are located using the expected geospatial coordinates of the line endpoints and are removed by using opencv medianFilter


* Tiling 
    * tiles from zoom level 2-15 were created
    * a modified version of `gdal2tiles.py` from `gdal` main branch was used to tile the sheets into a TMS tile map  
        * this version has support for parallel creation of overview tiles
        * also has `webp` support which I added on top( I do plan to give it back to `gdal` )
            * `webp` was used because of the significant space reduction it offered
    * also created a retiling script to retile only the affected tiles without needing to do it all over again( takes almost a day )
