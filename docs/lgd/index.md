---
layout: page
title: LGD
permalink: /lgd/
custom-js-list:
  - url: "/assets/js/lgd/flatpickr.min.js"
  - url: "/assets/js/lgd/archive_common.js"
  - url: "/assets/js/lgd/archive_picker.js"
custom-css-list:
  - url: "/assets/css/lgd/flatpickr_dark_custom.min.css"
  - url: "/assets/css/lgd/status.css"
---

Collection of Data from [Local Government Directory](https://lgdirectory.gov.in)

[Code](https://github.com/ramSeraph/opendata//tree/master/lgd) used to extract this data.


# Notes


Some of the data present here is also available at [data.gov.in](https://data.gov.in/catalog/local-government-directory-lgd)(updated monthly)

The archives use a zip format which is not understood by the standard unix `unzip` tool. Use [7zip](https://www.7-zip.org/) to extract the data from the archives instead. 


# Data


[List Of All Daily Archives](archives)

[Description](anatomy) of data in the archive


# Get Archive for date

---
<div id="archive_date" class="flatpickr"></div>
<br>
<span id='form_status'></span>
