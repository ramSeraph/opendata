
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

window.onload = (event) => {
    console.log('on window load')

    var hasError = false
    var statusSpan = document.getElementById('form_status')
    setStatus = (msg, error) => {
        // TODO: add colors based on error flag
        statusSpan.innerHTML = msg
        hasError = error
    }
    setStatus('', false)

    getArchiveForDate = (forDate) => {
        dateStr = getDateStr(forDate, false)
        setStatus(`Getting link for archive as of date ${dateStr}.. `, false)
        console.log('getting archive for date', dateStr)
        var httpRequest = new XMLHttpRequest()
    
        alertContents = () => {
            if (httpRequest.readyState === XMLHttpRequest.DONE) {
                if (httpRequest.status === 200) {
                    var jsonResponse = JSON.parse(httpRequest.responseText)
                    var bucket = jsonResponse['bucket']
                    var object = jsonResponse['name']
                    var size = fileSize(jsonResponse['size'])
                    setStatus(`<a href=https://storage.googleapis.com/${bucket}/${object}>${object}</a> ${size}`, false)
                } else {
                    if (httpRequest.status === 404) {
                        setStatus(`Archive not available for ${dateStr}`, true)
                    } else {
                        setStatus('Remote Request failed', true)
                        console.log(`Remote Request failed with ${httpRequest.status} and text: ${httpRequest.responseText}`)
                    }
                }
            }
        }
    
        if (!httpRequest) {
            setStatus('Internal Error', true)
            console.log('Giving up :( Cannot create an XMLHTTP instance')
            return
        }
        httpRequest.onreadystatechange = alertContents

        objName = getDateStr(forDate, true) + '.zip'
        bucketName = 'lgd_data_archive'
        httpRequest.open('GET', `https://storage.googleapis.com/storage/v1/b/${bucketName}/o/${objName}`)
        httpRequest.send()
        console.log('call sent')
        return httpRequest
    }

    var dateInput = document.getElementById('archive_date')
    // TODO: make this show local date
    var dateValue = new Date()
    dateInput.valueAsDate = dateValue
    httpRequest = getArchiveForDate(dateValue)
    prevDateValue = dateValue

    dateInput.onchange = () => {
        dateValue = dateInput.valueAsDate
        console.log('new date', dateValue)
        // TODO: in case previous remote called failed.. we might consider trying again
        if (prevDateValue.getTime() === dateValue.getTime()) {
            return
        }
        if ( ![XMLHttpRequest.DONE, XMLHttpRequest.UNSENT].includes(httpRequest.readyState)) {
            httpRequest.abort()
        }
        prevDateValue = dateValue;
        httpRequest = getArchiveForDate(dateValue)
    }
}

