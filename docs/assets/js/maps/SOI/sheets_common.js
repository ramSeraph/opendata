
function fileSize(size) {
    var i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
}

bucketName = 'soi_data'

parseListing = (listingText) => {
    var entryTexts = listingText.split('\n')
    var sizeMap = {}
    for (var entryText of entryTexts) {
        entryText = entryText.trim()
        if (entryText === '') {
            continue
        }
        var pieces = entryText.split(' ')
        sizeMap[pieces[1]] = pieces[0]
    }
    return sizeMap
}

const releasesUrlPrefix = 'https://github.com/ramSeraph/opendata/releases/download'

function fetchSheetList(releaseName, callback) {
    var url = `${releasesUrlPrefix}/${releaseName}/list.txt`
    var httpRequest = new XMLHttpRequest()
    
    alertContents = () => {
        if (httpRequest.readyState === XMLHttpRequest.DONE) {
            if (httpRequest.status === 200) {
                var sizeMap = parseListing(httpRequest.responseText)
                callback(null, sizeMap)
            } else {
                callback('Remote Request failed', null)
                console.log(`Remote Request failed with ${httpRequest.status} and text: ${httpRequest.responseText}`)
            }
        }
    }
     
    if (!httpRequest) {
        callback('Internal Error', null)
        console.log('Giving up :( Cannot create an XMLHTTP instance')
        return
    }
    httpRequest.onreadystatechange = alertContents
    httpRequest.open('GET', url)
    httpRequest.send()
    console.log('call sent')
}

function getStatusData(cb) {
    var gtiffSizeData = null
    var pdfSizeData = null
    var err = null

    collate = () => {
        if (gtiffSizeData === null || pdfSizeData === null) {
            return
        }
        if (err !== null) {
            cb(err, null)
            return
        }
        var statusInfo = {}
        for (sheetNo in pdfSizeData) {
            var name = `${sheetNo}.pdf`
            var sheetSize = pdfSizeData[sheetNo]
            var url = null
            var status = 'found'
            if (sheetNo.endsWith('.unavailable')) {
                status = 'not_found'
                name = name.replace('.unavailable', '')
            } else {
                url = `${releasesUrlPrefix}/soi-pdfs/${name}`
            }

            var sheetNoDisp = name.replace('_', '/').replace('.pdf', '')
            var fsize = fileSize(pdfSizeData[sheetNo])
            var info = {}
            if (!(sheetNoDisp in statusInfo)) {
                statusInfo[sheetNoDisp] = {}
            }
            statusInfo[sheetNoDisp]['status'] = status
            statusInfo[sheetNoDisp]['pdfUrl'] = url
            statusInfo[sheetNoDisp]['pdfFilesize'] = fsize
        }


        for (sheetNo in gtiffSizeData) {
            var name = `${sheetNo}.tif`
            var url = `${releasesUrlPrefix}/soi-tiffs/${name}`
            var sheetNoDisp = name.replace('_', '/').replace('.tif', '')
            var fsize = fileSize(gtiffSizeData[sheetNo])
            var info = {}
            if (!(sheetNoDisp in statusInfo)) {
                statusInfo[sheetNoDisp] = {}
            }
            statusInfo[sheetNoDisp]['status'] = 'parsed'
            statusInfo[sheetNoDisp]['gtiffUrl'] = url
            statusInfo[sheetNoDisp]['gtiffFilesize'] = fsize
        }
        cb(null, statusInfo)
    }

    fetchSheetList('soi-tiffs', (e, results) => {
        gtiffSizeData = results
        console.log('gtiff data callback invoked')
        collate()
    })

    fetchSheetList('soi-pdfs.txt', (e, results) => {
        pdfSizeData = results
        console.log('pdf data callback invoked')
        collate()
    })

}
