
// uses fileSize, getDateParts, monthNames, getArchiveList from archive_common.js

displayResults = (sizeMap) => {
    var archivesDiv = document.getElementById('archive_list')
    var objInfos = []

    for (const dateStr in sizeMap) {
        var objInfo = getDateParts(dateStr)
        objInfo['url'] = `https://storage.googleapis.com/${bucketName}/${dateStr}.zip`
        objInfo['size'] = fileSize(sizeMap[dateStr])
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

window.onload = (event) => {
    console.log('on window load')

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
    update = (data, error) => {
        if (error === true) {
            setStatus(data, true)
            return
        }

        setStatus('', false)
        displayResults(data)
    }
    getArchiveList(update)
}

