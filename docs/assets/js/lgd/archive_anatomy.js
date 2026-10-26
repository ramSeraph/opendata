document.addEventListener('DOMContentLoaded', function() {
    fetch('/opendata/lgd/site_map.json')
        .then(response => response.json())
        .then(data => {
            const compMap = parseSiteMap(data);
            const anatomyContent = document.getElementById('anatomy-content');
            anatomyContent.innerHTML = '';
            Object.keys(compMap).forEach(key => {
                const item = compMap[key];
                if (item.comp && item.fields) {
                    const section = document.createElement('section');
                    section.className = 'report-section';
                    section.setAttribute('aria-labelledby', key);
                    const header = document.createElement('header');
                    header.className = 'report-heading';
                    const h2 = document.createElement('h2');
                    h2.id = key;
                    const link = document.createElement('a');
                    link.href = '#' + key;
                    const filename = document.createElement('code');
                    filename.textContent = key + '.csv';
                    link.appendChild(filename);
                    h2.appendChild(link);
                    header.appendChild(h2);
                    if (item.comp === "IGNORE") {
                        const status = document.createElement('span');
                        status.className = 'report-status';
                        status.textContent = 'No longer active';
                        header.appendChild(status);
                    }
                    section.appendChild(header);

                    const description = document.createElement('p');
                    description.className = 'report-description';
                    description.textContent = item.desc;
                    section.appendChild(description);

                    const dl = document.createElement('dl');

                    if (item.dropdown && item.dropdown.length > 0) {
                        const dtLocation = document.createElement('dt');
                        dtLocation.textContent = 'Location in LGD:';
                        dl.appendChild(dtLocation);
                        const ddLocation = document.createElement('dd');
                        const ul = document.createElement('ul');
                        let currentUl = ul;
                        item.dropdown.forEach((level, index) => {
                            const li = document.createElement('li');
                            li.textContent = level;
                            currentUl.appendChild(li);
                            if (index < item.dropdown.length - 1) {
                                const newUl = document.createElement('ul');
                                li.appendChild(newUl);
                                currentUl = newUl;
                            }
                        });
                        ddLocation.appendChild(ul);
                        dl.appendChild(ddLocation);
                    }

                    const dtFields = document.createElement('dt');
                    dtFields.textContent = 'Fields';
                    dl.appendChild(dtFields);
                    const ddFields = document.createElement('dd');
                    const table = createFieldsTable(item.fields);
                    table.setAttribute('aria-label', key + '.csv fields');
                    table.querySelectorAll('th').forEach(th => th.scope = 'col');
                    ddFields.appendChild(table);
                    dl.appendChild(ddFields);

                    section.appendChild(dl);
                    anatomyContent.appendChild(section);
                }
            });
            const anchor = document.getElementById(decodeURIComponent(location.hash.slice(1)));
            if (anchor) anchor.scrollIntoView();
        })
        .catch(error => {
            document.getElementById('anatomy-content').textContent = 'The report descriptions could not be loaded. Reload this page to try again.';
            console.error('Error loading site_map.json:', error);
        });
});

