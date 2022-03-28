(() => {
    var gaId = JSON.parse(document.getElementById('ga_data').textContent)['id']
    
    window[`ga-disable-${gaId}`] = window.doNotTrack === "1" || navigator.doNotTrack === "1" || navigator.doNotTrack === "yes" || navigator.msDoNotTrack === "1";
    
    window.dataLayer = window.dataLayer || [];
    
    function gtag() {
        window.dataLayer.push(arguments)
    }
    gtag('js', new Date())
    gtag('config', gaId, {
        cookie_flags: 'max-age=7200;secure;samesite=strict'
    })
})();
