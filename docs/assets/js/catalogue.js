(() => {
  "use strict";
  const scriptURL = new URL(document.currentScript.src);
  const root = new URL("../../", scriptURL);
  const lgd = new URL("lgd/", root);
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => Number(n).toLocaleString("en-IN");
  const esc = (s) =>
    String(s ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const date = (s) =>
    s
      ? new Date(s + "T00:00:00Z").toLocaleDateString("en-GB", {
          day: "numeric",
          month: "short",
          year: "numeric",
          timeZone: "UTC",
        })
      : "Event report";
  const size = (n) =>
    n >= 1048576
      ? (n / 1048576).toFixed(1) + " MiB"
      : (n / 1024).toFixed(1) + " KiB";
  function set(id, value) {
    if ($(id)) $(id).textContent = value;
  }
  function render(data) {
    const available = data.datasets.filter((d) => d.file);
    set("dataset-total", fmt(available.length));
    set("parquet-total", size(available.reduce((n, d) => n + d.bytes, 0)));
    set("government-total", fmt(data.scopes.length));
    set("unit-total", fmt(data.scopes.reduce((n, s) => n + s.units, 0)));
    set(
      "organization-total",
      fmt(data.scopes.reduce((n, s) => n + s.organizations, 0)),
    );
    set(
      "home-dataset-total",
      fmt(available.length) + " datasets · Parquet + source archives",
    );
    const dates = available
      .map((d) => d.observed_on)
      .filter(Boolean)
      .sort();
    set(
      "catalogue-date",
      "Snapshot source dates: " +
        date(dates[0]) +
        (dates[0] === dates.at(-1) ? "" : " – " + date(dates.at(-1))) +
        ". Each report keeps its own date.",
    );
    if (!$("dataset-rows")) return;
    const category = $("dataset-category"),
      query = $("dataset-search");
    for (const name of [
      ...new Set(data.datasets.map((d) => d.category)),
    ].sort()) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      category.append(option);
    }
    const params = new URLSearchParams(location.search);
    if (params.has("q")) query.value = params.get("q");
    if ([...category.options].some((o) => o.value === params.get("category")))
      category.value = params.get("category");
    function filter() {
      const term = query.value.trim().toLowerCase();
      const matches = data.datasets.filter(
        (d) =>
          (!category.value || d.category === category.value) &&
          [d.name, d.description, d.category]
            .join(" ")
            .toLowerCase()
            .includes(term),
      );
      $("dataset-rows").innerHTML = matches
        .map(
          (d) =>
            '<tr><td><span class="dataset-name">' +
            esc(d.name) +
            '</span><span class="description">' +
            esc(d.description) +
            '</span></td><td><span class="observation">' +
            (d.file ? date(d.observed_on) : "Not published") +
            "</span>" +
            (d.status === "failed" || d.status === "blocked"
              ? '<span class="description">Update ' +
                esc(d.status) +
                "; last available file</span>"
              : "") +
            '</td><td><span class="row-count">' +
            (d.rows == null ? "—" : fmt(d.rows)) +
            "</span></td><td>" +
            (d.file
              ? '<div class="download-links"><a href="' +
                esc(new URL(d.file, lgd).href) +
                '" download>Parquet ↓</a><a href="' +
                esc(new URL(d.manifest, lgd).href) +
                '">Schema ↗</a></div><span class="size">' +
                size(d.bytes) +
                "</span>"
              : '<span class="description">Unavailable' +
                (d.reason ? ": " + esc(d.reason) : "") +
                "</span>") +
            "</td></tr>",
        )
        .join("");
      set(
        "dataset-count",
        fmt(matches.length) + " of " + fmt(data.datasets.length) + " datasets",
      );
      $("dataset-empty").hidden = Boolean(matches.length);
      $("dataset-table").hidden = !matches.length;
      const url = new URL(location.href);
      url.searchParams.delete("q");
      url.searchParams.delete("category");
      if (query.value) url.searchParams.set("q", query.value);
      if (category.value) url.searchParams.set("category", category.value);
      history.replaceState(null, "", url);
    }
    query.addEventListener("input", filter);
    category.addEventListener("change", filter);
    filter();
    const address = new URL("data/metadata.json", lgd).href;
    if ($("access-code"))
      $("access-code").textContent =
        `const index = await fetch(\n  '${address}'\n).then(r => r.json());\n\nconst states = index.datasets.states.daily.file;\nconst parquet = await fetch(states.url)\n  .then(r => r.arrayBuffer());`;
    if ($("metadata-link")) $("metadata-link").href = address;
  }
  fetch(new URL("catalogue.json", lgd))
    .then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(render)
    .catch(() => {
      if ($("catalogue-error")) $("catalogue-error").hidden = false;
      set(
        "dataset-count",
        "The catalogue could not be loaded. Reload to try again.",
      );
      set(
        "catalogue-date",
        "Source dates are available in each dataset’s metadata.",
      );
    });
})();
