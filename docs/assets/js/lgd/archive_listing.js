
function buildFileHTML(fileInfo) {
    const fileSize = formatFileSize(fileInfo.size);
    return `<li><a href="${fileInfo.url}">${fileInfo.filename}</a> (${fileSize})</li>`;
}

function displayArchives(data, elementId, isMonthly) {
    const container = document.getElementById(elementId);
    if (!container) return;

    let allFiles = [];
    for (const component in data) {
        if (component === 'changes' || (typeof ignoredComponents !== 'undefined' && ignoredComponents.has(component.toUpperCase()))) continue;
        for (const date in data[component]) {
            allFiles.push(data[component][date]);
        }
    }

    // Sort files by date, newest first
    allFiles.sort((a, b) => {
        let dateA, dateB;
        if (isMonthly) {
            const datePartA = a.filename.split('.')[1];
            const yearA = datePartA.substring(3);
            const monthAbbrA = datePartA.substring(0, 3);
            const monthNumA = monthMap[monthAbbrA];
            dateA = new Date(`${yearA}-${monthNumA}-01`);

            const datePartB = b.filename.split('.')[1];
            const yearB = datePartB.substring(3);
            const monthAbbrB = datePartB.substring(0, 3);
            const monthNumB = monthMap[monthAbbrB];
            dateB = new Date(`${yearB}-${monthNumB}-01`);
        } else {
            dateA = new Date(convertDateToYYYYMMDD(a.filename.split('.')[1]));
            dateB = new Date(convertDateToYYYYMMDD(b.filename.split('.')[1]));
        }
        return dateB - dateA;
    });

    let html = '<ul>';
    let filesByYear = {};

    for (const fileInfo of allFiles) {
        let year, month, day;
        if (isMonthly) {
            const datePart = fileInfo.filename.split('.')[1];
            year = datePart.substring(3);
            const monthAbbr = datePart.substring(0, 3);
            month = monthNames[parseInt(monthMap[monthAbbr]) - 1]; // Convert numerical month to full name
            day = 'all'; // For monthly archives, we don't have a specific day
        } else {
            const datePart = fileInfo.filename.split('.')[1];
            year = datePart.substring(5, 9);
            const monthAbbr = datePart.substring(2, 5);
            month = monthNames[parseInt(monthMap[monthAbbr]) - 1]; // Convert numerical month to full name
            day = datePart.substring(0, 2);
        }

        if (!filesByYear[year]) {
            filesByYear[year] = {};
        }
        if (!filesByYear[year][month]) {
            filesByYear[year][month] = {};
        }
        if (!filesByYear[year][month][day]) {
            filesByYear[year][month][day] = [];
        }
        filesByYear[year][month][day].push(fileInfo);
    }

    const sortedYears = Object.keys(filesByYear).sort((a, b) => b - a);

    for (const year of sortedYears) {
        html += `<li>${year}<ul>`;
        const sortedMonths = Object.keys(filesByYear[year]).sort((a, b) => monthNames.indexOf(b) - monthNames.indexOf(a));
        for (const month of sortedMonths) {
            html += `<li>${month}<ul>`;
            const sortedDays = Object.keys(filesByYear[year][month]).sort((a, b) => b - a);
            for (const day of sortedDays) {
                if (!isMonthly) {
                    html += `<li>${day}<ul>`;
                }
                for (const fileInfo of filesByYear[year][month][day]) {
                    html += buildFileHTML(fileInfo);
                }
                if (!isMonthly) {
                    html += '</ul></li>';
                }
            }
            html += '</ul></li>';
        }
        html += '</ul></li>';
    }
    html += '</ul>';
    container.innerHTML = html;
}


document.addEventListener('DOMContentLoaded', function() {
    var status = document.getElementById('call_status');
    if (status) {
        status.textContent = 'Loading files...';
        status.style.color = 'black';
    }

    Promise.all([
        fetch('/opendata/lgd/listing_files.csv').then(response => response.text()),
        fetch('/opendata/lgd/archives/listing_files.csv').then(response => response.text())
    ])
    .then(([currentFilesData, monthlyFilesData]) => {
        const currentFiles = parseFileListings(currentFilesData, false);
        const monthlyFiles = parseFileListings(monthlyFilesData, true);

        displayArchives(currentFiles, 'current_archives', false);
        displayArchives(monthlyFiles, 'monthly_archives', true);

        if (status) {
            status.textContent = ''; // Clear loading message
        }
    })
    .catch(error => {
        console.error('Error loading data:', error);
        if (status) {
            status.textContent = `Error loading data: ${error.message || error}`;
            status.style.color = 'red';
        }
    });
});
