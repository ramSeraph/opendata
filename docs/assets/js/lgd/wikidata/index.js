

function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

function showError(txt) {
  const div = getMainDiv();
  const textElem = document.createTextNode(`ERROR: ${txt} !!!`);
  div.appendChild(textElem);
}

function renderSection(k, entries, el) {
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
    list.insertAdjacentHTML('beforeend', `<li id=${k}>${k}:</li>`);
    const le = document.getElementById(k);
    renderSection(k, v, le);
    count += 1;
    // add corrections
    const header_inst = getInstance(k, v[0]);
    const header = header_inst.getQSHeader(); 
    if (header === null) {
      continue;
    }
    list.insertAdjacentHTML('beforeend', `<li id=${k}_corrections>${k}_corrections:</li>`);
    const cle = document.getElementById(`${k}_corrections`);
    var corrections = header + '<br/>';
    for (const entry of v) {
      const inst = getInstance(k, entry);
      const row = inst.getQSRow();
      corrections += row;
      corrections += '<br/>';
    }
    cle.insertAdjacentHTML('beforeend', `<ul><span role="textbox">${corrections}</span></ul>`);
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
  const jsonUrl = `https://storage.googleapis.com/lgd_wikidata_reports/${entity}s.json`;
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

function addStatus(status) {
  for (const [k,v] of Object.entries(status)) {
    const span = document.getElementById(k);
    var statusText = 'CLEAR';
    if (v !== 0) {
      statusText = '!! HAS PROBLEMS !!';
    }
    span.insertAdjacentHTML('beforeend', ` - ${statusText}`);
  }
}

function addLinks(entities, entity_info) {
  const div = getMainDiv();
  div.insertAdjacentHTML('beforeend', '<h1>Reports:</h1>');
  div.insertAdjacentHTML('beforeend', '<ul id="linklist"></ul>');
  const list = document.getElementById('linklist');
  const baseUrl = window.location.toString();
  for (const e of entities) {
    const entityLink = `<a href='${baseUrl}?entity=${e}'>${e}s</a>`;
    const queryLink = `<a href='${entity_info[e]["query"]}' target="_blank">query</a>`;
    list.insertAdjacentHTML('beforeend', `<li><span id="${e}">${entityLink} - ${queryLink}</span></li>`);
  }
  const jsonUrl = 'https://storage.googleapis.com/lgd_wikidata_reports/status.json';
  fetch(jsonUrl)
    .then(response => {
      if (response.ok) {
        return response.json();
      }
      throw new Error("couldn't retreive status file");
    })
    .then(json => addStatus(json))
    .catch((error) => {
      showError(error.message);
    });

}

function getMainDiv() {
  return document.getElementById('main');
}

function main() {
  const entities = [ 'state', 'division', 'district', 'subdivision', 'subdistrict' ];
  const entity_info = {
    'state': { 'query': 'https://query.wikidata.org/index.html#SELECT%20%3Fitem%20%3FitemLabel%20%3FstateORutLabel%20%3FlgdCode%0AWHERE%0A%7B%0A%20%20%23%20subclass%20of%20state%20or%20Union%20Territory%20of%20India%0A%20%20%3Fitem%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ131541.%0A%20%20%3Fitem%20wdt%3AP31%20%3FstateORut.%0A%20%20OPTIONAL%20%7B%20%3Fitem%20wdt%3AP6425%20%3FlgdCode%20%7D.%0A%20%20%23%20not%20a%20proposed%20entity%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ64728694%20%7D%29%0A%20%20%23%20not%20a%20dissolved%20entity%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP576%20%3Fdt.%20%7D%29%0A%20%20%23%20not%20replaced%20by%20anything%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP1366%20%3Fdt.%20%7D%29%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D' },
    'division': {'query': 'https://query.wikidata.org/index.html#SELECT%20%3Fitem%20%3FitemLabel%20%3Fstate%20%3FstateLabel%0AWHERE%0A%7B%0A%20%20%23%20subclass%20of%20division%20of%20India%0A%20%20%3Fitem%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ1230708.%0A%20%20%3Fitem%20wdt%3AP131%20%3Fstate.%0A%20%20%23%20not%20a%20proposed%20entity%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ64728694%20%7D%29%0A%20%20%23%20not%20a%20dissolved%20entity%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP576%20%3Fdt.%20%7D%29%0A%20%20%23%20not%20replaced%20by%20anything%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP1366%20%3Fdt.%20%7D%29%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D'},
    'district': {'query': 'https://query.wikidata.org/index.html#SELECT%20%3Fitem%20%3FitemLabel%20%3Fdivision%20%3FdivisionLabel%20%3Fstate%20%3FstateLabel%20%3FlgdCode%0AWHERE%0A%7B%0A%20%20%23%20subclass%20of%20district%20of%20India%0A%20%20%3Fitem%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ1149652.%0A%20%20OPTIONAL%20%7B%20%3Fitem%20wdt%3AP6425%20%3FlgdCode%20%7D.%0A%20%20%7B%0A%20%20%20%20%3Fitem%20wdt%3AP131%20%3Fdivision.%0A%20%20%20%20%3Fdivision%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ1230708.%0A%20%20%20%20%3Fdivision%20wdt%3AP131%20%3Fstate.%0A%20%20%7D%0A%20%20UNION%0A%20%20%7B%0A%20%20%20%20%3Fitem%20wdt%3AP131%20%3Fstate.%0A%20%20%20%20%3Fstate%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ131541.%0A%20%20%7D%0A%20%20%23%20not%20a%20proposed%20entity%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP31%2Fwdt%3AP279%2a%20wd%3AQ64728694%20%7D%29%0A%20%20%23%20not%20a%20dissolved%20entity%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP576%20%3Fdt.%20%7D%29%0A%20%20%23%20not%20replaced%20by%20anything%0A%20%20FILTER%28NOT%20EXISTS%20%7B%20%3Fitem%20wdt%3AP1366%20%3Fdt.%20%7D%29%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7'},
    'subdivision': {'query': 'TODO'},
    'subdistrict': {'query': 'TODO'},
  };

  const params = new Proxy(new URLSearchParams(window.location.search), {
    get: (searchParams, prop) => searchParams.get(prop),
  });
  const qEntity = params.entity;

  if (qEntity === null) {
    addLinks(entities, entity_info);
  } else if (entities.includes(qEntity)) {
    showPage(qEntity);
  } else {
    showError(`unknown param "${qEntity}"!!!`);
  }
}

document.addEventListener("DOMContentLoaded", function(event){
  main();
});
