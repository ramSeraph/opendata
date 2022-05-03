
function fileSize(size) {
    var i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) * 1 + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
}

function displayData(items) {
    var sheetsDiv = document.getElementById('sheets_list')
    var objInfos = []
    for (obj of items) {
        var name = obj['name']
        var bucket = obj['bucket']
        if (! name.endsWith('.pdf')) {
            continue
        }
        var sheetName = name.replace('.pdf', '').replace('_', '/').replace('raw/', '')

        var objInfo = {}
        objInfo['name'] = sheetName
        objInfo['size'] = fileSize(obj['size'])
        objInfo['url'] = `https://storage.googleapis.com/${bucket}/${name}`
        objInfos.push(objInfo)
    }
    var allHtml = ''
    allHtml += '<ul>'
    for (info of objInfos) {
        allHtml += `<li><a href="${info['url']}">${info['name']}</a> ${info['size']}</li>`
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
    fetchSheetList(fetchListCb)
}
