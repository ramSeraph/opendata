
// uses fileSize, getDateParts, bucketName from archive_common.js

function getDateStr(d, forArchive) {
    var ye = new Intl.DateTimeFormat('en', { year: 'numeric' }).format(d);
    var mo = new Intl.DateTimeFormat('en', { month: 'short' }).format(d);
    var ml = new Intl.DateTimeFormat('en', { month: 'long' }).format(d);
    var da = new Intl.DateTimeFormat('en', { day: '2-digit' }).format(d);
    if (forArchive === true) {
        return `${da}${mo}${ye}`
    }
    return `${da} ${ml} ${ye}`
}

function getDateRange(dstrs) {
    var minDate = null
    var maxDate = null
    for (let dstr of dstrs) {
        const date = getDateParts(dstr)['date']
        if (minDate === null || date < minDate) {
            minDate = date
        }

        if (maxDate === null || date > maxDate) {
            maxDate = date
        }
    }

    return { minDate, maxDate }
}

function showLink(date, sizeMap, statusSetter) {
    const dateStr = getDateStr(date, true)
    const objName = dateStr + '.zip'
    const size = fileSize(sizeMap[dateStr])
    statusSetter(`Archive: <a href=https://storage.googleapis.com/${bucketName}/${objName} >${objName}</a> ${size}`, false)
}


function setupDatePicker(el, statusSetter, sizeMap) {
    
    var { minDate, maxDate } = getDateRange(Object.keys(sizeMap)) 

    flatpickr(el, {
        'inline': true,
        // 'clickOpens': false,
        // 'static': true,
        'dateFormat': "",
        // 'position': "above",
        'minDate': minDate,
        'maxDate': new Date(),
        'defaultDate': maxDate,
        'disable': [ (d) => { const k = getDateStr(d, true); return !(k in sizeMap) } ], 
        'onChange': [ (sdates, ddstr, inst) => { showLink(sdates[0], sizeMap, statusSetter) } ]
    });
    showLink(maxDate, sizeMap, statusSetter)
}

window.onload = (event) => {
    console.log('on window load')

    var statusSpan = document.getElementById('form_status')
    setStatus = (msg, error, selected) => {
        if (statusSpan.hasAttribute("class")) {
            statusSpan.removeAttribute("class")
        }
        statusSpan.innerHTML = msg
        if (error) {
            statusSpan.setAttribute("class", "error")
        }
    }
    setStatus(`Getting list of all archives.. `, false)
    var datepicker = document.getElementById("archive_date")

    fillDatePicker = (data, error) => {
        if (error === true) {
            setStatus(data, true)
            return
        }
        setStatus('', false)
        setupDatePicker(datepicker, setStatus, data)
    }

    getArchiveList(fillDatePicker)
}

