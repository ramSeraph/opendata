document.addEventListener('DOMContentLoaded', function() {
    fetch('/opendata/lgd/site_map.json')
        .then(response => response.json())
        .then(data => {
            compMap = parseSiteMap(data);
            const anatomyContent = document.getElementById('anatomy-content');
            Object.keys(compMap).forEach(key => {
                const item = compMap[key];
                if (item.comp && item.fields) {
                    const h2 = document.createElement('h2');
                    h2.id = key;
                    var heading = key + '.csv';
                    if (item.comp === "IGNORE") {
                        heading += ' (No longer active)';
                    }
                    h2.textContent = heading;
                    anatomyContent.appendChild(h2);

                    const dl = document.createElement('dl');
                    
                    const dtDesc = document.createElement('dt');
                    dtDesc.textContent = 'description:';
                    dl.appendChild(dtDesc);
                    const ddDesc = document.createElement('dd');
                    ddDesc.textContent = item.desc;
                    dl.appendChild(ddDesc);

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
                    dtFields.textContent = 'Expected fields:';
                    dl.appendChild(dtFields);
                    const ddFields = document.createElement('dd');
                    ddFields.appendChild(createFieldsTable(item.fields));
                    dl.appendChild(ddFields);

                    anatomyContent.appendChild(dl);
                    anatomyContent.appendChild(document.createElement('hr'));
                }
            });
        })
        .catch(error => console.error('Error loading site_map.json:', error));
});

