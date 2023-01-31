
function fileSize(size) {
    var i = Math.floor(Math.log(size) / Math.log(1024));
    return (size / Math.pow(1024, i)).toFixed(2) * 1 + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
}

getDateStr = (d, forArchive) => {
    var ye = new Intl.DateTimeFormat('en', { year: 'numeric' }).format(d);
    var mo = new Intl.DateTimeFormat('en', { month: 'short' }).format(d);
    var ml = new Intl.DateTimeFormat('en', { month: 'long' }).format(d);
    var da = new Intl.DateTimeFormat('en', { day: '2-digit' }).format(d);
    if (forArchive === true) {
        return `${da}${mo}${ye}`
    }
    return `${da} ${ml} ${ye}`
}

var monthNames = ["January", "February", "March", "April",
                  "May", "June", "July", "August", "September",
                  "October", "November", "December"]
var monthMap = {}
for (m of monthNames) {
    monthMap[m.substring(0,3)] = m
}

getDateParts = (name) => {
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

bucketName = 'lgd_data_archive'
listFileName = 'listing_archives.txt'

displayResults = (sizeMap) => {
    var archivesDiv = document.getElementById('archive_list')
    var objInfos = []

    for (const dateStr in sizeMap) {
        var objInfo = getDateParts(dateStr)
        objInfo['url'] = `https://storage.googleapis.com/${bucketName}/${dateStr}.zip`
        objInfo['size'] = sizeMap[dateStr]
        objInfo['name'] = `${dateStr}.zip`
        objInfos.push(objInfo)
    }

    var objInfoMap = {}
    for (objInfo of objInfos) {
        var year = objInfo['year']
        var month = objInfo['month']
        var day = objInfo['day']
        if (!(year in objInfoMap)) {
            objInfoMap[year] = {}
        }
        if (!(month in objInfoMap[year])) {
            objInfoMap[year][month] = {}
        }
        objInfoMap[year][month][day] = {
            'url': objInfo['url'],
            'size': objInfo['size'],
            'name': objInfo['name'],
        }
    }

    var allHtml = ''
    var years = Object.keys(objInfoMap)
    years.sort((y1, y2) => {
        return parseInt(y1) - parseInt(y2)
    })
    allHtml += '<ul>'
    for (year of years) {
        allHtml += '<li>'
        allHtml += `${year}\n`
        var monthWiseMap = objInfoMap[year]
        var months = Object.keys(monthWiseMap)
        months.sort((m1, m2) => {
            return monthNames.indexOf(m1) - monthNames.indexOf(m2)
        })
        allHtml += '<ul>'
        for (month of months) {
            allHtml += '<li>'
            allHtml += `${month}\n`
            var dayWiseMap = monthWiseMap[month]
            var days = Object.keys(dayWiseMap)
            days.sort((d1, d2) => {
                return parseInt(d1) - parseInt(d2)
            })
            allHtml += '<ul>'
            for (day of days) {
                var info = dayWiseMap[day]
                allHtml += `<li><a href="${info['url']}">${info['name']}</a> ${info['size']}</li>`
            }
            allHtml += '</ul>'
            allHtml += '</li>'
        }
        allHtml += '</ul>'
        allHtml += '</li>'
    }
    allHtml += '</ul>'
    archivesDiv.innerHTML = allHtml
}


parseListing = (listingText) => {
    var entryTexts = listingText.split('\n')
    var sizeMap = {}
    for (var entryText of entryTexts) {
        var pieces = entryText.split(' ')
        sizeMap[pieces[1]] = pieces[0]
    }
    return sizeMap
}


window.onload = (event) => {
    console.log('on window load')

    var hasError = false
    var statusSpan = document.getElementById('call_status')
    setStatus = (msg, error) => {
        statusSpan.innerHTML = msg
        if (error) {
            statusSpan.setAttribute("class", "error")
        } else if (statusSpan.hasAttribute("class")) {
            statusSpan.removeAttribute("class")
        }
    }
    setStatus(`Getting list of all archives.. `, false)
    console.log('getting list of all archives')
    var httpRequest = new XMLHttpRequest()
    
    alertContents = () => {
        if (httpRequest.readyState === XMLHttpRequest.DONE) {
            if (httpRequest.status === 200) {
                var sizeMap = parseListing(httpRequest.responseText)
                setStatus('', false)
                displayResults(sizeMap)
            } else {
                setStatus('Remote Request failed', true)
                console.log(`Remote Request failed with ${httpRequest.status} and text: ${httpRequest.responseText}`)
            }
        }
    }
    
    if (!httpRequest) {
        setStatus('Internal Error', true)
        console.log('Giving up :( Cannot create an XMLHTTP instance')
        return
    }
    httpRequest.onreadystatechange = alertContents
    httpRequest.open('GET', `https://storage.googleapis.com/${bucketName}/${listFileName}`)
    httpRequest.send()
    console.log('call sent')
}

