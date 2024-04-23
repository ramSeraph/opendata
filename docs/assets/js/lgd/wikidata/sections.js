function wd_url(wd_id) {
  return `https://www.wikidata.org/wiki/${wd_id}`;
}

function wd_link(wd_id, wd_name) {
  if (wd_id === null || wd_id === undefined) {
    return wd_name;
  }
  const url = wd_url(wd_id);
  return `<a href="${url}" target="_blank">${wd_name}</a>`;
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
  static getQSHeader() {
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
  static getQSHeader() {
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
  static getQSHeader() {
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
    return `LGD id: ${this.data['lgd_code']}, Curr: ${currLink}, Prev: ${prevLink}`;
  }
  getQSRow() {
    return null;
  }
  static getQSHeader() {
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
  static getQSHeader() {
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
  static getQSHeader() {
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
        /* TODO: add the remaining fields */
        liHTMLs += `<li>${lgdEntry['lgd_name']} - ${lgdEntry['lgd_code']}</li>`;
    }
    return `<span>${link}</span><ul>${liHTMLs}</ul>`;
  }
  getQSRow() {
    return null;
  }
  static getQSHeader() {
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
    return `${lgdEntry['lgd_name']} - ${lgdEntry['lgd_code']}`;
  }
  /* TODO: add corrections */
  getQSRow() {
    return null;
  }
  static getQSHeader() {
    return null;
  }
}

class NameMismatch {
  constructor(data) {
    this.data = data;
  }
  getHTML() {
    const link = wd_link(this.data['wikidata_id'], this.data['wikidata_label']);
    const lgdEntry = this.data['lgd_entry'];
    /* TODO: add extra fields */
    return `${lgdEntry['lgd_name']} - ${lgdEntry['lgd_code']}, ${link}`;
  }
  /* TODO: add corrections */
  getQSRow() {
    return null;
  }
  static getQSHeader() {
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
  static getQSHeader() {
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
  }
  return inst;
}
