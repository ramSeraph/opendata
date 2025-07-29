function fileSize(size) {
    var i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
}

parseListing = (listingText) => {
    var entryTexts = listingText.trim().split('\n');
    var data = {};
    // skip header
    for (var i = 1; i < entryTexts.length; i++) {
        var entryText = entryTexts[i].trim();
        if (entryText === '') {
            continue;
        }
        var pieces = entryText.split(',');
        if (pieces.length < 3) continue;
        var name = pieces[0];
        var size = pieces[1];
        var url = pieces[2];
        data[name] = { size: size, url: url };
    }
    return data;
}

function fetchSheetList(listFilename, callback) {
    var url = `../${listFilename}`
    var httpRequest = new XMLHttpRequest()
    
    alertContents = () => {
        if (httpRequest.readyState === XMLHttpRequest.DONE) {
            if (httpRequest.status === 200) {
                var data = parseListing(httpRequest.responseText)
                callback(null, data)
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
        for (const name in pdfSizeData) {
            const pdfInfo = pdfSizeData[name];
            const sheetNoDisp = name.replace('_', '/').replace('.pdf', '');
            const fsize = fileSize(pdfInfo.size);
            if (!(sheetNoDisp in statusInfo)) {
                statusInfo[sheetNoDisp] = {};
            }
            statusInfo[sheetNoDisp]['status'] = 'found';
            statusInfo[sheetNoDisp]['pdfUrl'] = pdfInfo.url;
            statusInfo[sheetNoDisp]['pdfFilesize'] = fsize;
        }


        for (const name in gtiffSizeData) {
            const gtiffInfo = gtiffSizeData[name];
            const sheetNoDisp = name.replace('_', '/').replace('.tif', '');
            const fsize = fileSize(gtiffInfo.size);
            if (!(sheetNoDisp in statusInfo)) {
                statusInfo[sheetNoDisp] = {};
            }
            statusInfo[sheetNoDisp]['status'] = 'parsed';
            statusInfo[sheetNoDisp]['gtiffUrl'] = gtiffInfo.url;
            statusInfo[sheetNoDisp]['gtiffFilesize'] = fsize;
        }
        cb(null, statusInfo)
    }

    fetchSheetList('tiff_listing.csv', (e, results) => {
        if (e) {
            err = e;
        }
        gtiffSizeData = results
        console.log('gtiff data callback invoked')
        collate()
    })

    fetchSheetList('pdf_listing.csv', (e, results) => {
        if (e) {
            err = e;
        }
        pdfSizeData = results
        console.log('pdf data callback invoked')
        collate()
    })

}
