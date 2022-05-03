
function fetchSheetList(callback) {
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
    bucketName = 'soi_data'
    prefix = 'raw/'
    httpRequest.open('GET', `https://storage.googleapis.com/storage/v1/b/${bucketName}/o?prefix=${prefix}&maxResults=6500`)
    httpRequest.send()
    console.log('call sent')
}
