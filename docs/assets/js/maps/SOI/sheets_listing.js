
function displayData(statusInfo) {
    console.log(statusInfo)
    var sheetsDiv = document.getElementById('sheets_list')
    var allHtml = ''
    allHtml += '<ul>'
    for (sheetNo in statusInfo) {
        var info = statusInfo[sheetNo]
        if (info['status'] === 'not_found') {
            continue
        }
        allHtml += `<li>${sheetNo}`
        allHtml += '<ul>'
        if ('gtiffUrl' in info) {
            allHtml += `<li><a href="${info['gtiffUrl']}">gtiff</a> ${info['gtiffFilesize']}</li>`
        }
        /* if ('pdfUrl' in info) {
            allHtml += `<li><a href="${info['pdfUrl']}">pdf</a> ${info['pdfFilesize']}</li>`
        } */
        allHtml += '</ul>'
        allHtml += '</li>'
    }
    allHtml += '</ul>'
    sheetsDiv.innerHTML = allHtml
}

function fetchListCb(err, data) {
    var statusSpan = document.getElementById('call_status')
    if (err !== null) {
        console.log(err)
        statusSpan.setAttribute("class", "error")
        statusSpan.innerHTML = "Error!! Couldn't get status list"
    } else {
        statusSpan.innerHTML = ""
        displayData(data)
    }
}

window.onload = (event) => {
    var statusSpan = document.getElementById('call_status')
    statusSpan.innerHTML = 'Fetching sheet list..'
    getStatusData(fetchListCb)
}
