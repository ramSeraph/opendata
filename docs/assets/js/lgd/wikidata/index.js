

function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

function showError(txt) {
  const div = getMainDiv();
  const textElem = document.createTextNode(`ERROR: ${txt} !!!`);
  div.appendChild(textElem);
}

function renderSection(k, entries, el) {
  if (entries.length == 0) {
    return
  }
  el.insertAdjacentHTML('beforeend', `<ul id="entrylist_${k}"></ul>`);
  const l = document.getElementById(`entrylist_${k}`);
  for (const entry of entries) {
    const inst = getInstance(k, entry);
    const entryHTML = inst.getHTML();
    l.insertAdjacentHTML('beforeend', `<li>${entryHTML}</li>`);
  }
}

function renderSections(list, data) {
  var count = 0;
  for (const [k, v] of Object.entries(data)) {
    if (v.length === 0) {
      continue;
    }
    list.insertAdjacentHTML('beforeend', `<li id=${k}><h2>${k}</h2></li>`);
    const le = document.getElementById(k);
    renderSection(k, v, le);
    count += 1;
  }
  if (count === 0) {
    const div = getMainDiv();
    const textElem = document.createTextNode('ALL SYNCED');
    div.appendChild(textElem);
  }
}

function showPage(entity) {
  const div = getMainDiv();
  const reportType = capitalizeFirstLetter(entity);
  div.insertAdjacentHTML('beforeend', `<h1>${reportType} Report:</h1>`);
  div.insertAdjacentHTML('beforeend', '<ul id="sectionlist"></ul>');
  const list = document.getElementById('sectionlist');
  const jsonUrl = `https://storage.googleapis.com/lgd_wikidata_reports/${entity}s.json`
  fetch(jsonUrl)
    .then(response => {
      if (response.ok) {
        return response.json();
      }
      throw new Error("couldn't retreive report file");
    })
    .then(json => renderSections(list, json))
    .catch((error) => {
      showError(error.message);
    });
}

function addLinks(entities) {
  const div = getMainDiv();
  div.insertAdjacentHTML('beforeend', '<h1>Reports:</h1>');
  div.insertAdjacentHTML('beforeend', '<ul id="linklist"></ul>');
  const list = document.getElementById('linklist');
  entities.forEach((e) => list.insertAdjacentHTML('beforeend', `<li><a href="javascript:location.search+='&entity=${e}';">${e}s</a></li>`));
}

function getMainDiv() {
  return document.getElementById('main');
}

function main() {
  const entities = [ 'state', 'division', 'district', 'subdivision', 'subdistrict' ];

  const params = new Proxy(new URLSearchParams(window.location.search), {
    get: (searchParams, prop) => searchParams.get(prop),
  });
  const qEntity = params.entity;

  if (qEntity === null) {
    addLinks(entities);
  } else if (entities.includes(qEntity)) {
    showPage(qEntity);
  } else {
    showError(`unknown param "${qEntity}"!!!`);
  }
}

document.addEventListener("DOMContentLoaded", function(event){
  main();
});
