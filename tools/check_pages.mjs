import fs from "node:fs/promises";
import assert from "node:assert/strict";

const base = process.argv[2] || "http://localhost:8030/opendata/";
const port = process.env.LGD_GRAPH_CDP_PORT || 9231;
const version = await (
  await fetch(`http://127.0.0.1:${port}/json/version`)
).json();
const socket = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});
let seq = 0;
const pending = new Map(),
  errors = [];
socket.addEventListener("message", (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id) {
    const p = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) p.reject(new Error(JSON.stringify(msg.error)));
    else p.resolve(msg.result);
  } else if (msg.method === "Runtime.exceptionThrown")
    errors.push(msg.params.exceptionDetails);
});
function call(method, params = {}, sessionId) {
  const id = ++seq;
  socket.send(
    JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }),
  );
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
const { targetId } = await call("Target.createTarget", { url: "about:blank" });
const { sessionId } = await call("Target.attachToTarget", {
  targetId,
  flatten: true,
});
const send = (method, params = {}) => call(method, params, sessionId);
async function evaluate(expression) {
  const r = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(expression) {
  for (let i = 0; i < 120; i++) {
    if (await evaluate(expression)) return;
    await wait(250);
  }
  throw new Error("Timed out: " + expression);
}
async function navigate(path) {
  await send("Page.navigate", { url: new URL(path, base).href });
  await until(`document.readyState==='complete'`);
}
const click = (selector) =>
  evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
async function screenshot(name) {
  await wait(180);
  const r = await send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: false,
  });
  await fs.writeFile(
    "/private/tmp/opendata-" + name + ".png",
    Buffer.from(r.data, "base64"),
  );
}
try {
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1040,
    deviceScaleFactor: 1,
    mobile: false,
  });
  const catalogue = await (
    await fetch(new URL("lgd/catalogue.json", base))
  ).json();
  const available = catalogue.datasets.filter((d) => d.file);
  await navigate("");
  await until(
    `!document.getElementById('home-dataset-total').textContent.startsWith('Parquet')`,
  );
  await screenshot("home-desktop");
  assert.equal(
    await evaluate('document.querySelectorAll(".collection-card").length'),
    3,
  );
  await navigate("lgd/");
  await until(`document.getElementById('unit-total').textContent!=='—'`);
  assert.equal(
    await evaluate(
      `Number(document.getElementById('unit-total').textContent.replaceAll(',',''))`,
    ),
    catalogue.scopes.reduce((n, s) => n + s.units, 0),
  );
  await screenshot("lgd-desktop");
  await navigate("lgd/datasets/");
  await until(`document.querySelectorAll('#dataset-rows tr').length>0`);
  assert.equal(
    await evaluate(`document.querySelectorAll('#dataset-rows tr').length`),
    catalogue.datasets.length,
  );
  assert(
    await evaluate(
      `Array.from(document.querySelectorAll('#dataset-rows a')).every(a=>a.origin===location.origin)`,
    ),
    "Every Parquet/schema download must be hosted on Pages",
  );
  await screenshot("datasets-desktop");
  await evaluate(
    `document.getElementById('dataset-search').value='central_org';document.getElementById('dataset-search').dispatchEvent(new Event('input'))`,
  );
  assert.equal(
    await evaluate(`document.querySelectorAll('#dataset-rows tr').length`),
    3,
  );
  await evaluate(
    `document.getElementById('dataset-search').value='no_such_dataset';document.getElementById('dataset-search').dispatchEvent(new Event('input'))`,
  );
  assert.equal(
    await evaluate(`document.getElementById('dataset-empty').hidden`),
    false,
  );
  await evaluate(
    `document.getElementById('dataset-search').value='';document.getElementById('dataset-category').value='Organizations';document.getElementById('dataset-category').dispatchEvent(new Event('change'))`,
  );
  assert.equal(
    await evaluate(`document.querySelectorAll('#dataset-rows tr').length`),
    catalogue.datasets.filter((d) => d.category === "Organizations").length,
  );
  const states = catalogue.datasets.find((d) => d.name === "states");
  const binary = await evaluate(
    `(async()=>{const r=await fetch(${JSON.stringify(new URL("lgd/" + states.file, base).href)});const b=new Uint8Array(await r.arrayBuffer());return{ok:r.ok,length:b.length,head:new TextDecoder().decode(b.slice(0,4)),tail:new TextDecoder().decode(b.slice(-4))};})()`,
  );
  assert.equal(binary.ok, true);
  assert.equal(binary.length, states.bytes);
  assert.equal(binary.head, "PAR1");
  assert.equal(binary.tail, "PAR1");
  // A different origin can read the same public files, as on GitHub Pages.
  // A raw data document has no application CSP. Test CORS from there so the
  // catalogue's self-only connect policy does not mask the server's headers.
  await navigate("lgd/data/metadata.json");
  const otherOrigin = new URL(base);
  otherOrigin.hostname = "127.0.0.1";
  assert.equal(
    await evaluate(
      `(async()=>{const r=await fetch(${JSON.stringify(new URL("lgd/" + states.file, otherOrigin).href)});return(await r.arrayBuffer()).byteLength;})()`,
    ),
    states.bytes,
  );
  const metadata = await (
    await fetch(new URL("lgd/data/metadata.json", base))
  ).json();
  for (const d of Object.values(metadata.datasets).filter((d) => d.daily)) {
    for (const ref of [d.daily.file, d.manifest])
      assert(
        ref.url.startsWith("https://ramseraph.github.io/opendata/lgd/data/"),
      );
  }
  await navigate("lgd/archives/");
  await until(
    `document.querySelectorAll('#component_selector option').length>1`,
  );
  await evaluate(
    `document.getElementById('component_selector').value='states';document.getElementById('component_selector').dispatchEvent(new Event('change'))`,
  );
  await until(`Boolean(document.querySelector('#file_info a'))`);
  assert.equal(
    await evaluate(`document.getElementById('date_picker_container').hidden`),
    false,
  );
  assert(
    await evaluate(
      `document.getElementById('file_info').textContent.includes('states.')`,
    ),
  );
  await screenshot("archives-desktop");
  await navigate("lgd/anatomy/");
  await until(`document.querySelectorAll('#anatomy-content h2').length>20`);
  await navigate("lgd/organizations/");
  await until(`Boolean(globalThis.lgdExplorer?.ready)`);
  assert.equal(
    await evaluate(`document.querySelectorAll('#scope-select option').length`),
    catalogue.scopes.length,
  );
  assert.equal(
    await evaluate(`lgdExplorer.model.rows('central_org_units').length`),
    catalogue.scopes.find((s) => s.code === "0").units,
  );
  assert.equal(
    await evaluate(
      `document.getElementById('packed-data').textContent.trim().length`,
    ),
    0,
    "Web shell must load Centre lazily",
  );
  assert.equal(
    await evaluate(
      `document.querySelector('.brand-mark').getAttribute('href')`,
    ),
    "../",
  );
  assert.equal(await evaluate(`[...lgdExplorer.model.nodes.values()].some(n=>n.kind==='group')`), false);
  const largeOrg = await evaluate(`lgdExplorer.model.organizations.map(n=>({id:n.id,count:lgdExplorer.model.displayChildIds(n.id).length})).sort((a,b)=>b.count-a.count)[0]`);
  assert(largeOrg.count > 10000, "Exercise a large organization without grouping nodes");
  await evaluate(`lgdExplorer.focus(${JSON.stringify(largeOrg.id)})`);
  assert.equal(await evaluate('lgdExplorer.view.nodes.length'), largeOrg.count + 1);
  assert(await evaluate(`lgdExplorer.view.edges.every(e=>e.label===(lgdExplorer.model.node(e.target).kind==='unit'?'organization membership':'parent organization'))`));
  await wait(150);
  assert((await evaluate('lgdExplorer.view.drawnNodes')) < 60, "Only paint units in the viewport");
  assert((await evaluate('document.querySelectorAll("#child-list [data-jump]").length')) < 30);
  await screenshot("organization-direct-units");
  await evaluate(
    `document.getElementById('search').value='depatment telecomunication';document.getElementById('search').dispatchEvent(new Event('input'))`,
  );
  await until(
    `Boolean(document.querySelector('#search-results [data-jump="org:1066"]'))`,
  );
  assert.equal(
    await evaluate(
      `document.querySelector('#search-results .result-item').dataset.jump`,
    ),
    "org:1066",
  );
  await evaluate(
    `document.getElementById('search').value='';document.getElementById('search').dispatchEvent(new Event('input'))`,
  );
  await evaluate(`lgdExplorer.focus('unit:1991846')`);
  assert.equal(
    await evaluate(`document.querySelector('[data-coverage]').disabled`),
    true,
  );
  assert.equal(
    await evaluate(
      `lgdExplorer.view.edges.filter(e=>e.source==='unit:1991846').length`,
    ),
    10,
  );
  const telecomExpected = await evaluate(`lgdExplorer.model.unitDesignationIds(lgdExplorer.model.node('unit:1245288')).length`);
  assert((await evaluate(`lgdExplorer.model.node('designations:1066').count`))>=2,'Unmatched title rows must remain in the organization catalogue');
  await evaluate(
    `lgdExplorer.focus('org:1066');lgdExplorer.expandTitles('unit:1245288')`,
  );
  assert.equal(
    await evaluate(
      `lgdExplorer.view.nodes.filter(n=>n.kind==='designation').length`,
    ),
    telecomExpected,
  );
  await click('[data-jump="designations:1066"]');
  assert.equal(await evaluate('lgdExplorer.state.selected'),'designations:1066');
  await evaluate(`lgdExplorer.focus('org:1066');lgdExplorer.expandTitles('unit:1245288')`);
  await screenshot("organizations-desktop");
  await evaluate(`lgdExplorer.changeScope('28')`);
  await until(`lgdExplorer.ready&&lgdExplorer.state.scope==='28'`);
  assert.equal(
    await evaluate(`lgdExplorer.model.rows('state_org_units').length`),
    catalogue.scopes.find((s) => s.code === "28").units,
  );
  await evaluate(`lgdExplorer.focus('unit:1320513')`);
  assert(
    (await evaluate(`lgdExplorer.view.nodes.length`)) > 10000,
    "Large branches must still expand without paging",
  );
  await evaluate(`lgdExplorer.changeScope('0')`);
  await until(`lgdExplorer.ready&&lgdExplorer.state.scope==='0'`);
  assert.equal(await evaluate(`lgdExplorer.state.focus`), "org:1066");
  assert.equal(
    await evaluate(
      `lgdExplorer.view.nodes.filter(n=>n.kind==='designation').length`,
    ),
    telecomExpected,
  );
  await evaluate(`lgdExplorer.changeScope('9')`);
  await until(`lgdExplorer.ready&&lgdExplorer.state.scope==='9'`);
  const fuzzyTime = await evaluate(
    `(()=>{const start=performance.now();const matches=lgdExplorer.model.search('depatment educaton');return{ms:performance.now()-start,matches:matches.length};})()`,
  );
  assert(fuzzyTime.matches > 0);
  assert(
    fuzzyTime.ms < 1500,
    "Fuzzy search should stay responsive in the largest state: " +
      JSON.stringify(fuzzyTime),
  );
  await send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  });
  for (const path of [
    "",
    "lgd/",
    "lgd/datasets/",
    "lgd/archives/",
    "lgd/organizations/",
  ]) {
    await navigate(path);
    if (path.includes("organizations"))
      await until(`Boolean(globalThis.lgdExplorer?.ready)`);
    else if (path === "lgd/datasets/")
      await until(`document.querySelectorAll('#dataset-rows tr').length>0`);
    assert(
      await evaluate(`document.documentElement.scrollWidth<=innerWidth+1`),
      "Page overflows at mobile width: " + path,
    );
    if (path === "" || path === "lgd/datasets/")
      await screenshot(path === "" ? "home-mobile" : "datasets-mobile");
  }
  assert.deepEqual(errors, [], "Unexpected browser exceptions");
  console.log(
    JSON.stringify(
      {
        passed: true,
        datasets: available.length,
        governments: catalogue.scopes.length,
        fuzzySearchLargestState: fuzzyTime,
        checks: [
          "responsive pages",
          "dataset search and categories",
          "Pages-only downloads",
          "binary Parquet access",
          "cross-origin fetch",
          "source archive picker",
          "field guide",
          "lazy Centre and state loading",
          "disabled empty controls",
          "Telecom unit titles",
          "large branch expansion",
          "scope view restoration",
        ],
      },
      null,
      2,
    ),
  );
} catch (error) {
  await screenshot("failure").catch(() => {});
  throw error;
} finally {
  await call("Target.closeTarget", { targetId });
  socket.close();
}
