---
layout: page
title: LGD
permalink: /lgd/
---

Collection of Data from [Local Government Directory](https://lgdirectory.gov.in)

# Notes

Some of the data present here is also available at [data.gov.in](https://data.gov.in/catalog/local-government-directory-lgd)(updated monthly)

The archives use a zip format which is not understood by the standard unix `unzip` tool. Use [7zip](https://www.7-zip.org/) to extract the data from the archives instead. 

[List Of All Daily Archives](archives)

[Description](anatomy) of data in the archive

[Code](https://github.com/ramSeraph/opendata//tree/master/lgd) used to extract this data.

# Get Archive for date


<link rel="stylesheet" property="stylesheet" type="text/css" href="{{ "/assets/css/lgd/status.css" | relative_url }}">
<script src="{{ "/assets/js/lgd/archive_searcher.js" | relative_url }}" ></script>
<form name='archive_search_form'>
  <input type="date" id="archive_date" name="date" text="Get LGD archive link for date: " autocomplete="off" />
</form>

<span id='form_status'></span>
<span id='archive_list'></span>
