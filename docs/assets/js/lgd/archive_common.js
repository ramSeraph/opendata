var monthNames = ["January", "February", "March", "April",
                  "May", "June", "July", "August", "September",
                  "October", "November", "December"]
var monthMap = {}
for (m of monthNames) {
    monthMap[m.substring(0,3)] = m
}

function formatFileSize(size) {
    var i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
}

var monthMap = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
};

var monthMapReverse = {}; 
for (var key in monthMap) {
    if (monthMap.hasOwnProperty(key)) {
        monthMapReverse[monthMap[key]] = key;
    }
}

function getDateParts(name) {
    var day = name.substring(0,2)
    var month = monthMap[name.substring(2,5)]
    var year = name.substring(5,9)

    return {
        'day': day,
        'month': month,
        'year': year,
        'date': new Date(`${year}-${month}-${day}`)
    }
}


function convertDateToDDBBBYYYY(dateStr) {
  var parts = dateStr.split('-');
  if (parts.length !== 3) {
    throw new Error("Invalid date format. Expected format: YYYY-MM-DD");
  }
  var year = parts[0];
  var month = parts[1];
  var day = parts[2];
  var monthAbbr = monthMapReverse[month];
  if (!monthAbbr) {
    throw new Error("Invalid month value: " + month);
  }
  return `${day}${monthAbbr}${year}`;
}

function convertDateToYYYYMMDD(dateStr) {
    var dateInfo = getDateParts(dateStr);
    return dateInfo.date.toISOString().split('T')[0]; // Returns YYYY-MM-DD format
}

function convertMonth(dateStr) {
    var monthAbbr = dateStr.substring(0, 3);
    var year = dateStr.substring(3, 7);
    var month = monthMap[monthAbbr];
    var monthYear = `${year}-${month}`;
    return monthYear;
}

function parseSiteMap(siteMapData) {
    var componentInfo = {};

    siteMapData.forEach(item => {
        if (!item.comp) return;
        if (item.comp === "IGNORE" && !item.fields) return;
        if (!item.file) return;
        var key = item.file.toLowerCase().replace('.csv', '');                  
        delete item.file; // Remove file property from item
        componentInfo[key] = item; // Store the item in componentInfo
    });
    return componentInfo;
}

function parseFileListings(listingFilesData, expectMonth) {
    var infos = {};
    var lines = listingFilesData.split('\n');
    for (var i = 1; i < lines.length; i++) {

        var line = lines[i].trim();
        if (line === '') continue;

        var parts = line.split(',');
        var filename = parts[0];
        var size = parts[1];
        var url = parts[2];
        var filenameParts = filename.split('.');
        var datePart = filenameParts[filenameParts.length - 2];
        var componentName = filenameParts[0].toLowerCase(); // Use the first part as component name
        if (componentName === 'changes') {
            infos[componentName] = {
                size: size,
                url: url,
                filename: filename
            };
            continue; // Skip further processing for changes.csv.7z
        }

        var date = datePart;
        if (!expectMonth) {
          date = convertDateToYYYYMMDD(filenameParts[1]);
        } else {
          date = convertMonth(datePart);
        }

        if (!infos.hasOwnProperty(componentName)) {
            infos[componentName] = {};
        }
        infos[componentName][date] = {
            size: size,
            url: url,
            filename: filename
        };
    }

    return infos;
}

var ignoredComponents = new Set(['CODE_VERSION', 'DATA_SOURCES.MD', 'DATA_LICENSE']);

function createFieldsTable(fieldMap) {
    var table = document.createElement('table');
    var thead = document.createElement('thead');
    var tbody = document.createElement('tbody');

    var headerRow = document.createElement('tr');
    var th1 = document.createElement('th');
    th1.textContent = 'Field';
    var th2 = document.createElement('th');
    th2.textContent = 'Description';
    headerRow.appendChild(th1);
    headerRow.appendChild(th2);
    thead.appendChild(headerRow);

    for (var field in fieldMap) {
        var row = document.createElement('tr');
        var td1 = document.createElement('td');
        td1.textContent = field;
        var td2 = document.createElement('td');
        td2.textContent = fieldMap[field].description;
        row.appendChild(td1);
        row.appendChild(td2);
        tbody.appendChild(row);
    }

    table.appendChild(thead);
    table.appendChild(tbody);

    return table;
}

