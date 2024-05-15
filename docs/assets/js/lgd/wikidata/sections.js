function wd_url(wd_id) {
  return `https://www.wikidata.org/wiki/${wd_id}`;
}

function wd_link(wd_id, wd_name) {
  if (wd_id === null || wd_id === undefined) {
    return wd_name;
  }
  const url = wd_url(wd_id);
  var name = wd_name;
  if (name === 'NA') {
      name = wd_id;
  }
  return `<a href="${url}" target="_blank">${name}</a>`;
}

function renderLgdEntry(lgdEntry) {
  var out = '<ul>';
  for (const [k, v] of Object.entries(lgdEntry)){
    if (k.startsWith('lgd_')) {
      continue;
    }
    out += `<li>${k}: ${v}</li>`;
  }
  out += '</ul>';
  return out;
}

class NotInIndia {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    return `${link}`;
  }
  /* deal with entries with P17 already set */
  getQSRow() {
    return `${this.data['wikidata_id']},Q668`;
  }
  getQSHeader() {
    return 'qid,P17';
  }
}

class NoLGDId {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'],this.data['wikidata_label']);
    return `${link}`;
  }
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class UnknownLGDId {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'],this.data['wikidata_label']);
    return `${link} - LGD id: ${this.data['lgd_code']}`;
  }
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class DuplicateLGDId {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const currLink = wd_link(this.data['curr'], this.data['curr_label']);
    const prevLink = wd_link(this.data['prev'], this.data['prev_label']);
    const lgdEntry = this.data['lgd_entry'];
    const lgdStr = renderLgdEntry(lgdEntry);
    return `LGD id: ${lgdEntry['lgd_code']}, LGD Name: ${lgdEntry['lgd_name']}, Curr: ${currLink}, Prev: ${prevLink}${lgdStr}`;
  }
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class MultipleInstanceOf {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    var liHTMLs = '';
    for (const instEntry of this.data['inst_of_entries']) {
        const instLink = wd_link(instEntry['id'],instEntry['label']);
        liHTMLs += `<li>${instLink}</li>`;
    }
    return `<span>${link}</span><ul>${liHTMLs}</ul>`;
  }
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class MultipleLocatedIn {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'],this.data['wikidata_label']);
    var liHTMLs = '';
    for (const locEntry of this.data['located_in_entries']) {
        const locLink = wd_link(locEntry['id'], locEntry['label']);
        liHTMLs += `<li>${locLink}</li>`;
    }
    return `<span>${link}</span><ul>${liHTMLs}</ul>`;
  }
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class MultipleLGDIds {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'],this.data['wikidata_label']);
    var liHTMLs = '';
    for (const lgdEntry of this.data['lgd_entries']) {
      const lgdStr = renderLgdEntry(lgdEntry);
      liHTMLs += `<li>LGD Name: ${lgdEntry['lgd_name']}, LGD Code: ${lgdEntry['lgd_code']}${lgdStr}</li>`;
    }
    return `<span>${link}</span><ul>${liHTMLs}</ul>`;
  }
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class Missing {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const lgdEntry = this.data['lgd_entry'];
    /* TODO: add extra fields */
    const lgdStr = renderLgdEntry(lgdEntry);
    return `LGD Name: ${lgdEntry['lgd_name']}, LGD Code: <a href="${lgdEntry['lgd_url']}" target="_blank">${lgdEntry['lgd_code']}</a>${lgdStr}`;
  }
  getQSRow() {
    const w = this.data['correction_info'];
    return `,"${w['label']}","${w['desc']}",Q668,${w['inst_of']},${w['loc_in']},${w['inception']},"""${w['lgd_code']}""","""https://lgdirectory.gov.in/downloadDirectory.do?"""`
  }
  getQSHeader() {
    return 'qid,Len,Den,P17,P31,P131,P571,P6425,S854';
  }
}

class NameMismatch {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    const lgdEntry = this.data['lgd_entry'];
    const lgdStr = renderLgdEntry(lgdEntry);
    return `${link}, LGD Name: ${lgdEntry['lgd_name']}, LGD Code: ${lgdEntry['lgd_code']}${lgdStr}`;
  }
  /* TODO: add corrections */
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}


class WrongHierarchy {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    const lgdEntry = this.data['lgd_entry'];

    var expected_links = [];
    for (const e of this.data['expected']) {
      expected_links.push(wd_link(e['id'], e['label']));
    }
    const expected_links_str = expected_links.join(' --> ')

    var current_links = [];
    for (const e of this.data['current']) {
      current_links.push(wd_link(e['id'], e['label']));
    }
    const current_links_str = current_links.join(' --> ')

    return `<span>${link}</span><ul><li>Expected: ${expected_links_str}</li><li>Current: ${current_links_str}</li></ul>`;
  }
  /* TODO: add corrections */
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class WrongSuffix {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    const expected_suffix = this.data['expected_suffix'];
    return `<span>${link}</span><ul><li>Expected Suffix: ${expected_suffix}</li></ul>`;
  }
  /* TODO: add corrections */
  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class WrongInstOf {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    const expected_inst_of_entries = this.data['expected_inst_ofs'];
    const expected_inst_of_links = [];
    for (const e of expected_inst_of_entries) {
      expected_inst_of_links.push(wd_link(e['id'], e['label']));
    }
    const expected_links_str = expected_inst_of_links.join(' or ');
    const curr = this.data['current_inst_of'];
    const curr_inst_of_link = wd_link(curr['id'], curr['label']);
    return `<span>${link}</span><ul><li>Expected Instance Of: ${expected_inst_of_links}</li><li>Current Instance Of: ${curr_inst_of_link}</ul>`;
  }
  getQSRow() {
    const expected_inst_of_entries = this.data['expected_inst_ofs'];
    if (expected_inst_of_entries.length != 1) {
        return null;
    }
    const expected_id = expected_inst_of_entries[0]['id'];
    if (expected_id === undefined) {
        return null;
    }
    const curr_id = this.data['current_inst_of']['id'];
    const wd_id = this.data['wikidata_id'];
    return `${wd_id},${curr_id},${expected_id}`;
  }
  getQSHeader() {
    return 'qid,-P31,P31';
  }
}


class WrongKindOfLocatedIn {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    const curr = this.data['located_in'];
    const curr_loc_in_link = wd_link(curr['id'], curr['label']);
    return `<span>${link}</span><ul><li>Expected located in: ${this.data['expected']}</li><li>Current located in: ${curr_loc_in_link}</li></ul>`;
  }

  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class WrongKindOfContains {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    const contains = this.data['contains'];
    var lis = '';
    for (const c of contains) {
      const cLink = wd_link(c['curr']['id'], c['curr']['label']);
      const expected = c['expected'];
      lis += `<li>Curr: ${cLink}, Expected: ${expected}</li>`;
    }
    return `<span>${link}</span><ul>${lis}</ul>`;
  }

  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class MismatchInContains {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const parent = this.data['parent'];
    const link = wd_link(parent['id'], parent['label']);
    var child_lis = '';
    for (const c of this.data['children']) {
      const cLink = wd_link(c['id'], c['label']);
      child_lis += `<li>${cLink}</li>`;
    }
    var missing_lis = '';
    for (const c of this.data['missing']) {
      const cLink = wd_link(c['id'], c['label']);
      missing_lis += `<li>${cLink}</li>`;
    }
    var extra_lis = '';
    for (const c of this.data['extra']) {
      const elem = c['element'];
      const from = c['child'];
      const eLink = wd_link(elem['id'], elem['label']);
      const fLink = wd_link(from['id'], from['label']);
      extra_lis += `<li>${eLink} from ${fLink}</li>`;
    }

    var html = `<span>${link}</span>`;
    html += '<ul>';
    if (missing_lis !== '') {
      html += `<li>children:<ul>${child_lis}</ul></li>`;
      html += `<li>missing_subchildren:<ul>${missing_lis}</ul></li>`;
    }
    if (extra_lis !== '') {
      html += `<li>extra_subchildren:<ul>${extra_lis}</ul></li>`;
    }
    html += '</ul>';
    return html;;
  }

  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}

class NoSinglePreferredRank {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    return `<span>${link}</span><ul><li>Num with preferred rank: ${this.data['num_preferred']}</li></ul>`;
  }

  getQSRow() {
    return null;
  }
  getQSHeader() {
    return null;
  }
}


function getInstance(k, data) {
  var inst = null;
  if (k === 'multiple_lgd_ids') {
    inst = new MultipleLGDIds(data);
  } else if (k === 'multiple_located_in') {
    inst = new MultipleLocatedIn(data);
  } else if (k === 'multiple_instance_of') {
    inst = new MultipleInstanceOf(data);
  } else if (k === 'duplicate_lgd_id') {
    inst = new DuplicateLGDId(data);
  } else if (k === 'unknown_lgd_id') {
    inst = new UnknownLGDId(data);
  } else if (k === 'no_lgd_id') {
    inst = new NoLGDId(data);
  } else if (k === 'not_in_india') {
    inst = new NotInIndia(data);
  } else if (k === 'missing') {
    inst = new Missing(data);
  } else if (k === 'name_mismatch') {
    inst = new NameMismatch(data);
  } else if (k === 'wrong_hierarchy') {
    inst = new WrongHierarchy(data);
  } else if (k === 'wrong_suffix') {
    inst = new WrongSuffix(data);
  } else if (k === 'wrong_inst_of') {
    inst = new WrongInstOf(data);
  } else if (k === 'wrong_kind_of_located_in') {
    inst = new WrongKindOfLocatedIn(data);
  } else if (k === 'wrong_kind_of_contains') {
    inst = new WrongKindOfContains(data);
  } else if (k === 'mismatch_in_contains') {
    inst = new MismatchInContains(data);
  } else if (k === 'no_single_preferred_rank_for_located_in') {
    inst = new NoSinglePreferredRank(data);
  }
  return inst;
}
