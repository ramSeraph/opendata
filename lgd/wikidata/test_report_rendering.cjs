const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../docs/assets/js/lgd/wikidata/sections.js'), 'utf8'), context);

test('missing entities with unresolved parents cannot produce QuickStatements', () => {
  const data = {
    lgd_entry: {lgd_name: 'Example', lgd_code: '104', lgd_url: 'https://example.org'},
    correction_info: {
      label: 'Example', desc: 'Example panchayat', inst_of: 'Q2758248',
      loc_in: null, inception: '', lgd_code: '104', lgd_code_prop: 'P6425',
      unresolved_parent: 'Uttar Pradesh (LGD state 9)',
    },
  };
  const unresolved = context.getInstance('missing', data);
  assert.equal(unresolved.getQSRow(), null);
  assert.match(unresolved.getHTML(), /Unresolved parent: Uttar Pradesh/);
  assert.match(unresolved.getHTML(), /Correction unavailable/);
  assert.match(unresolved.getQSHeader(), /P131/);

  const resolved = context.getInstance('missing', {
    ...data, correction_info: {...data.correction_info, loc_in: 'Q1174', unresolved_parent: undefined},
  });
  assert.match(resolved.getQSRow(), /Q1174/);
  assert.doesNotMatch(resolved.getHTML(), /Correction unavailable/);
});

test('overlap reports show unresolved district mappings and incomplete extra checks', () => {
  const report = context.getInstance('mismatch_territory_overlaps', {
    wikidata_id: 'Q4001', wikidata_label: 'Example panchayat',
    missing: [], extra: [],
    unresolved: [{lgd_code: '790', label: 'Markapuram (LGD district 790; Wikidata mapping unresolved)'}],
  });
  assert.match(report.getHTML(), /LGD district 790/);
  assert.match(report.getHTML(), /extra overlaps not checked/);
  assert.equal(report.getQSRow(), null);
});

test('unavailable effective dates are visible and export as an empty inception', () => {
  for (const inception of [null, undefined, '']) {
    const report = context.getInstance('missing', {
      lgd_entry: {
        lgd_name: 'Example', lgd_code: '4', lgd_url: 'https://example.org',
        'Effective Date Error': '503 Server Error',
      },
      correction_info: {
        label: 'Example', desc: 'Example subdistrict', inst_of: 'Q122987719',
        loc_in: 'Q2001', inception, lgd_code: '4', lgd_code_prop: 'P12748',
      },
    });
    assert.match(report.getHTML(), /Effective Date Error: 503 Server Error/);
    assert.match(report.getQSRow(), /Q2001,,/);
    assert.doesNotMatch(report.getQSRow(), /null|undefined/);
  }
});
