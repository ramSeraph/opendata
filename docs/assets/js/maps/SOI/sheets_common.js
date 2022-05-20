
function fileSize(size) {
    var i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) * 1 + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
}

function fetchSheetListPaged(curToken, prefix, callback) {
    var httpRequest = new XMLHttpRequest()
    console.log(`paged fetch called with ${prefix} and ${curToken}`)
 
    alertContents = () => {
        if (httpRequest.readyState === XMLHttpRequest.DONE) {
            if (httpRequest.status === 200) {
                var jsonResponse = JSON.parse(httpRequest.responseText)
                callback(null, jsonResponse)
            } else {
                callback({ 'status' : httpRequest.status, 'responseText': httpRequest.responseText }, null)
            }
        }
    }
    
    if (!httpRequest) {
        setStatus('Internal Error', true)
        console.log('Giving up :( Cannot create an XMLHTTP instance')
        return
    }
    httpRequest.onreadystatechange = alertContents
    const bucketName = 'soi_data'
    var url = `https://storage.googleapis.com/storage/v1/b/${bucketName}/o?prefix=${prefix}&maxResults=5000`
    if (curToken !== null) {
        url += `&pageToken=${curToken}`
    }
    httpRequest.open('GET', url)
    httpRequest.send()
    console.log('call sent')
}

function fetchSheetList(prefix, callback) {

    var allResults = []
    function pageCallback(err, resp) {
        if (err !== null) {
            callback(err, allResults)
        } else {
            const items = resp['items']
            allResults.push(...items)
            if ('nextPageToken' in resp) { 
                const curToken = resp['nextPageToken']
                fetchSheetListPaged(curToken, prefix, pageCallback)
            } else {
                callback(null, allResults)
            }
        }
    }
    fetchSheetListPaged(null, prefix, pageCallback)
}


function getStatusData(cb) {
    var rawData = null
    var gtiffData = null
    var err = null

    collate = () => {
        if (rawData === null || gtiffData === null) {
            return
        }
        if (err !== null) {
            cb(err, null)
            return
        }
        var statusInfo = {}
        for (obj of rawData) {
            var name = obj['name']
            var bucket = obj['bucket']
            var url = `https://storage.googleapis.com/${bucket}/${name}`
            var status = 'found'
            if (name.endsWith('.unavailable')) {
                status = 'not_found'
                name = name.split('.').slice(0, -1).join('.')
            }
            if (!name.endsWith('.pdf')) {
                continue
            }
            var prefix = name.split('.').slice(0, -1).join('.')
            var sheetNo = prefix.replace('_', '/').replace('raw/', '')
            var filesize = fileSize(obj['size'])
            if (status === 'found') {
                statusInfo[sheetNo] = { status: status, pdfUrl: url, pdfFilesize: filesize }
            } else {
                statusInfo[sheetNo] = { status: status }
            }
        }
        for (obj of gtiffData) {
            var name = obj['name']
            var bucket = obj['bucket']
            var url = `https://storage.googleapis.com/${bucket}/${name}`
            var status = 'found'
            if (!name.endsWith('.tif')) {
                continue
            }
            var prefix = name.split('.').slice(0, -1).join('.')
            var sheetNo = prefix.replace('_', '/').replace('export/gtiffs/', '')
            var filesize = fileSize(obj['size'])
            var info = {}
            if (!(sheetNo in statusInfo)) {
                statusInfo[sheetNo] = {}
            }
            statusInfo[sheetNo]['status'] = 'found'
            statusInfo[sheetNo]['gtiffUrl'] = url
            statusInfo[sheetNo]['gtiffFilesize'] = filesize
        }
        cb(null, statusInfo)
    }

    fetchSheetList('raw/', (e, results) => {
        if (e !== null) {
            err = e
        }
        rawData = results
        console.log('raw data callback invoked')
        collate()
    })
    fetchSheetList('export/gtiffs/', (e, results) => {
        if (e !== null) {
            err = e
        }
        gtiffData = results
        console.log('gtiff data callback invoked')
        collate()
    })
}
