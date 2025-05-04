
var bucketName = 'lgd_data_archive';
var listFileName = 'listing_archives.txt';

var monthNames = ["January", "February", "March", "April",
                  "May", "June", "July", "August", "September",
                  "October", "November", "December"]
var monthMap = {}
for (m of monthNames) {
    monthMap[m.substring(0,3)] = m
}

function fileSize(size) {
    var i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
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

function parseListing(listingText) {
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


function getArchiveList(cb) {
    console.log('getting list of all archives')
    var httpRequest = new XMLHttpRequest()
    
    alertContents = () => {
        if (httpRequest.readyState === XMLHttpRequest.DONE) {
            if (httpRequest.status === 200) {
                var sizeMap = parseListing(httpRequest.responseText)
                cb(sizeMap, false)
            } else {
                console.log(`Remote Request failed with ${httpRequest.status} and text: ${httpRequest.responseText}`)
                cb('Remote Request failed', true)
            }
        }
    }
    
    if (!httpRequest) {
        cb('Internal Error', true)
        return
    }
    httpRequest.onreadystatechange = alertContents
    httpRequest.open('GET', `https://storage.googleapis.com/${bucketName}/${listFileName}`)
    httpRequest.send()
}

