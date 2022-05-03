
function fetchSheetListPaged(curToken, callback) {
    var httpRequest = new XMLHttpRequest()
 
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
    const prefix = 'raw/'
    var url = `https://storage.googleapis.com/storage/v1/b/${bucketName}/o?prefix=${prefix}&maxResults=5000`
    if (curToken !== null) {
        url += `&pageToken=${curToken}`
    }
    httpRequest.open('GET', url)
    httpRequest.send()
    console.log('call sent')
}

function fetchSheetList(callback) {

    var allResults = []

    pageCallback = (err, resp) => {
        if (err !== null) {
            callback(err, resp)
        } else {
            const items = resp['items']
            allResults.push(...items)
            if ('nextPageToken' in resp) { 
                const curToken = resp['nextPageToken']
                fetchSheetListPaged(curToken, pageCallback)
            } else {
                callback(null, allResults)
            }
        }
    }

    fetchSheetListPaged(null, pageCallback)
}
