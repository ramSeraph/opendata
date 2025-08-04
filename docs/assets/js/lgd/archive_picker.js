
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
        console.log("monthYear: " + monthYear);
        if (previousMonthsInfos[selectedComponent] && previousMonthsInfos[selectedComponent][monthYear]) {
            fileData = previousMonthsInfos[selectedComponent][monthYear];
            isMonthFile = true;
        }
    }

    if (fileData) {
        var span = document.createElement('span');
        span.textContent = 'Download ';
        fileInfoDiv.appendChild(span);

        var link = document.createElement('a');
        link.href = fileData.url;
        var fileSize = formatFileSize(fileData.size);
        link.textContent = fileData.filename;
        fileInfoDiv.appendChild(link);
        var sizeSpan = document.createElement('span');
        sizeSpan.textContent = ' (' + fileSize + ')';
        fileInfoDiv.appendChild(sizeSpan);
        if (isMonthFile) {
            var infoSpan = document.createElement('span');
            var dateStrConv = convertDateToDDBBBYYYY(dateStr);
            var filename = `${selectedComponent}.${dateStrConv}.csv`
            infoSpan.textContent = `[ File inside archive: ${filename} ]`;
            fileInfoDiv.appendChild(infoSpan);
        }
    } else {
        fileInfoDiv.textContent = 'File not found for this date.';
    }
    console.log("Selected date: " + dateStr);

}

function populateComponentInfo(selectedComponent, componentInfo, currentMonthInfos, previousMonthsInfos) {
    var componentInfoDiv = document.getElementById('component_info');

    // Clear previous info
    componentInfoDiv.innerHTML = '';

    let componentData = componentInfo[selectedComponent];

    if (componentData.fields) {
        var fieldsHeading = document.createElement('h3');
        fieldsHeading.textContent = 'Expected Fields';
        componentInfoDiv.appendChild(fieldsHeading);
        var fieldsTable = createFieldsTable(componentData.fields);
        componentInfoDiv.appendChild(fieldsTable);
    }

    if (selectedComponent === 'changes') {

        var fileData = currentMonthInfos['changes'];

        if (fileData) {
            var fileInfoDiv = getFileInfoDiv();
            var span = document.createElement('span');
            span.textContent = 'Download ';
            fileInfoDiv.appendChild(span);

            var link = document.createElement('a');
            link.href = fileData.url;
            var fileSize = formatFileSize(fileData.size);
            link.textContent = fileData.filename;
            fileInfoDiv.appendChild(link);
            var sizeSpan = document.createElement('span');
            sizeSpan.textContent = ' (' + fileSize + ')';
            fileInfoDiv.appendChild(sizeSpan);
        } else {
            fileInfoDiv.textContent = 'File not found for changes component.';
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

        var datePickerContainer = document.getElementById('date_picker_container');
        datePickerContainer.innerHTML = '<h3>Pick a Date</h3><div id="archive_date" class="flatpickr"></div>';
        datePickerContainer.style.display = 'block';

        flatpickr("#archive_date", {
            enable: availableDates,
            dateFormat: "Y-m-d", // Set to YYYY-MM-DD
            defaultDate: lastAvailableDate,
            inline: true,
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

        if (!selectedComponent) {
            return; // Do nothing if no component is selected
        }

        var fileInfoDiv = getFileInfoDiv();
        fileInfoDiv.innerHTML = ''; // Clear previous info

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
