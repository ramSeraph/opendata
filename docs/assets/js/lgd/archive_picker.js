
function getFileInfoDiv() {
    var componentInfoDiv = document.getElementById('component_info');
    var fileInfoDiv = document.getElementById('file_info');
    if (!fileInfoDiv) {
        fileInfoDiv = document.createElement('div');
        fileInfoDiv.id = 'file_info';
        componentInfoDiv.appendChild(fileInfoDiv);
    }
    fileInfoDiv.innerHTML = ''; // Clear previous info
    return fileInfoDiv;
}


function showArchiveFile(fileData, label, member, dateStr) {
    var fileInfoDiv = getFileInfoDiv();
    var card = document.createElement('div');
    card.className = 'archive-download';
    var header = document.createElement('div');
    header.className = 'archive-download-header';
    var details = document.createElement('div');
    var meta = document.createElement('div');
    meta.className = 'archive-download-meta';
    meta.textContent = label + ' · ' + formatFileSize(fileData.size);
    var filename = document.createElement('strong');
    filename.className = 'archive-download-name';
    filename.textContent = fileData.filename;
    details.append(meta, filename);
    var link = document.createElement('a');
    link.className = 'button primary';
    link.href = fileData.url;
    link.textContent = 'Download archive ↓';
    header.append(details, link);
    card.appendChild(header);

    if (member) {
        var extract = document.createElement('div');
        extract.className = 'archive-extract';
        var heading = document.createElement('p');
        var date = new Date(dateStr + 'T00:00:00Z').toLocaleDateString('en-GB', {
            day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'
        });
        heading.textContent = 'Extract the report for ' + date;
        var commandRow = document.createElement('div');
        commandRow.className = 'archive-command';
        var pre = document.createElement('pre');
        var code = document.createElement('code');
        code.textContent = '7z e ' + fileData.filename + ' ' + member;
        pre.appendChild(code);
        var copy = document.createElement('button');
        copy.type = 'button';
        copy.className = 'button';
        copy.textContent = 'Copy';
        copy.setAttribute('aria-label', 'Copy extraction command');
        var status = document.createElement('span');
        status.className = 'archive-copy-status';
        status.setAttribute('role', 'status');
        copy.addEventListener('click', async function () {
            try {
                await navigator.clipboard.writeText(code.textContent);
                status.textContent = 'Command copied.';
            } catch {
                var range = document.createRange();
                range.selectNodeContents(code);
                var selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
                status.textContent = 'Command selected. Press Ctrl+C or ⌘C to copy.';
            }
        });
        commandRow.append(pre, copy);
        extract.append(heading, commandRow, status);
        card.appendChild(extract);
    }
    fileInfoDiv.appendChild(card);
}

function showLinksforDate(selectedComponent, dateStr, currentMonthInfos, previousMonthsInfos) {
    // Display URL and size
    var fileInfoDiv = getFileInfoDiv();
    fileInfoDiv.innerHTML = ''; // Clear previous info


    var fileData = null;
    var isMonthFile = false;
    // Check current month files first (exact date match)
    if (currentMonthInfos[selectedComponent] && currentMonthInfos[selectedComponent][dateStr]) {
        fileData = currentMonthInfos[selectedComponent][dateStr];
    } else {
        // Check previous months files (month/year match)
        var monthYear = dateStr.substring(0, 7); // YYYY-MM
        if (previousMonthsInfos[selectedComponent] && previousMonthsInfos[selectedComponent][monthYear]) {
            fileData = previousMonthsInfos[selectedComponent][monthYear];
            isMonthFile = true;
        }
    }

    if (fileData) {
        var member = isMonthFile ? `${selectedComponent}.${convertDateToDDBBBYYYY(dateStr)}.csv` : null;
        showArchiveFile(fileData, isMonthFile ? 'Monthly archive' : 'Daily archive', member, dateStr);
    } else {
        fileInfoDiv.textContent = 'File not found for this date.';
    }

}

function populateComponentInfo(selectedComponent, componentInfo, currentMonthInfos, previousMonthsInfos) {
    var componentInfoDiv = document.getElementById('component_info');

    // Clear previous info
    componentInfoDiv.innerHTML = '';
    document.getElementById('date_picker_container').hidden = true;

    let componentData = componentInfo[selectedComponent];

    if (componentData.fields) {
        var fieldsHeading = document.createElement('h3');
        fieldsHeading.textContent = 'Expected Fields';
        componentInfoDiv.appendChild(fieldsHeading);
        var fieldsTable = createFieldsTable(componentData.fields);
        componentInfoDiv.appendChild(fieldsTable);
    }

    if (selectedComponent === 'changes' || selectedComponent === 'transactions') {

        var fileData = currentMonthInfos[selectedComponent];
        var fileInfoDiv = getFileInfoDiv();

        if (fileData) {
            showArchiveFile(fileData, 'Cumulative archive');
        } else {
            fileInfoDiv.textContent = 'File not found for ' + selectedComponent + ' component.';
        }
    } else {
        var availableDates = [];
        if (currentMonthInfos[selectedComponent]) {
            availableDates = availableDates.concat(Object.keys(currentMonthInfos[selectedComponent]));
        }
        if (previousMonthsInfos[selectedComponent]) {
            availableDates = availableDates.concat(previousMonthsInfos[selectedComponent].dates);
        }
        availableDates = [...new Set(availableDates)].sort();
        var lastAvailableDate = availableDates.length > 0 ? availableDates[availableDates.length - 1] : null;
        var firstAvailableDate = availableDates.length > 0 ? availableDates[0] : null;

        var datePickerContainer = document.getElementById('date_picker_container');
        datePickerContainer.innerHTML = '<h3>Pick a Date</h3><div id="archive_date" class="flatpickr"></div>';
        datePickerContainer.style.display = 'block';
        datePickerContainer.hidden = false;

        flatpickr("#archive_date", {
            enable: availableDates,
            dateFormat: "Y-m-d", // Set to YYYY-MM-DD
            defaultDate: lastAvailableDate,
            inline: true,
            minDate: firstAvailableDate,
            maxDate: lastAvailableDate,
            onChange: function(selectedDates, dateStr, instance) {
                showLinksforDate(selectedComponent, dateStr, currentMonthInfos, previousMonthsInfos);
            }
        });

        if (lastAvailableDate) {
            showLinksforDate(selectedComponent, lastAvailableDate, currentMonthInfos, previousMonthsInfos);
        }
    }
}

function populateDropdown(components, componentInfo, currentMonthInfos, previousMonthsInfos) {
    var componentInfoDiv = document.getElementById('component_info');
    var componentSelector = document.getElementById('component_selector');

    var option = document.createElement("option");
    option.value = "";
    option.text = "pick component";
    componentSelector.appendChild(option);

    for (var component of components) {
        var option = document.createElement("option");
        option.value = component;
        let componentData = componentInfo[component];
        if (componentData.desc) {
            option.text = `${component} (${componentData.desc})`;
        } else {
            option.text = component;
        }
        componentSelector.appendChild(option);
    }
  
    componentSelector.addEventListener('change', (event) => {
        var selectedComponent = event.target.value;
        componentInfoDiv.innerHTML = ''; // Clear previous info
        
        var datePickerContainer = document.getElementById('date_picker_container');
        datePickerContainer.innerHTML = '';
        datePickerContainer.style.display = 'none';

        var fileInfoDiv = getFileInfoDiv();
        fileInfoDiv.innerHTML = ''; // Clear previous info

        if (!selectedComponent) {
            return; // Do nothing if no component is selected
        }

        populateComponentInfo(selectedComponent, componentInfo, currentMonthInfos, previousMonthsInfos);

    });
}



document.addEventListener('DOMContentLoaded', function() {
    var status = document.getElementById('form_status');

    status.textContent = 'Loading files...';
    status.style.color = 'black';
    Promise.all([
        fetch('/opendata/lgd/site_map.json').then(response => response.json()),
        fetch('/opendata/lgd/listing_files.csv').then(response => response.text()),
        fetch('/opendata/lgd/archives/mapping.json').then(response => response.json()),
        fetch('/opendata/lgd/archives/listing_files.csv').then(response => response.text()) // New fetch
    ])
    .then(([siteMapData, listingFilesData, archivesMappingData, archivesListingFilesData]) => {

        var componentInfo = parseSiteMap(siteMapData);
        // Process siteMapData
        var currMonthInfos = parseFileListings(listingFilesData, false);
        var prevMonthsInfos = parseFileListings(archivesListingFilesData, true);
        var components = new Set();
        for (var key in currMonthInfos) {
            components.add(key);
        }
        for (var key in prevMonthsInfos) {
            components.add(key);
        }

        // Process archivesMappingData (previous months date list)
        for (var compKey in archivesMappingData) {
            if (ignoredComponents.has(compKey)) {
              continue
            }
            var componentName = compKey.toLowerCase(); 
            prevMonthsInfos[componentName]['dates'] = archivesMappingData[compKey].map(dateStr => convertDateToYYYYMMDD(dateStr));
        }

        var sortedComponents = Array.from(components).sort();
            
        populateDropdown(sortedComponents, componentInfo, currMonthInfos, prevMonthsInfos);
      
        status.textContent = ''; // Clear loading message

    })
    .catch(error => {
        console.error('Error loading data:', error);
        status.textContent = `Error loading data: ${error.message || error}`;
        status.style.color = 'red';
    });
});
