

function fetchSheetCb(err, data) {
    if (err !== null) {
        console.log(err)
        var statusSpan = document.getElementById('form_status')
        statusSpan.innerHTML = "Error!! Couldn't get status list"
    } else {
        updateObjList(data['items'])
    }
}

window.onload = (event) => {
    var statusSpan = document.getElementById('form_status')
    statusSpan.innerHTML = ''
    var sheetListElement = document.getElementById('sheet_list')
    fetchSheetList(fetchSheetCb)
    dateInput.onchange = () => {
    }
}
