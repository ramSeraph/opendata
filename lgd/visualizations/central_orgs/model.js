/* Shared graph model. Namespaces and every reported source row stay distinct. */
(function (global) {
  'use strict';
  const valid = v => v != null && v !== '' && v !== '0';
  const key = (...v) => JSON.stringify(v);
  const collator = new Intl.Collator(undefined, {numeric: true});
  const compare = (a, b) => collator.compare(a.name, b.name) || a.id.localeCompare(b.id);
  const designationId = r => 'designation:' + key(r.designation_code, r.organization_code, r.organization_level_code, r.organization_level_name);
  const designationLevelId = r => 'designation-level:' + key(r.organization_code, r.organization_level_code, r.organization_level_name);
  const unitDesignationId = (unitId, associationId) => 'unit-designation:' + key(unitId, associationId);
  const normalizeSearch = value => String(value ?? '').normalize('NFKD').toLowerCase()
    .replace(/[\u0300-\u036f]/g, '').replace(/[^\p{L}\p{N}\p{M}]+/gu, ' ').trim().replace(/\s+/g, ' ');
  const searchAliases = {dept:'department',deptt:'department',govt:'government'};
  // Bounded Damerau-Levenshtein distance against a word/prefix. Adjacent
  // transpositions count as one typo. The narrow band avoids quadratic work.
  function prefixDistance(term, word, limit) {
    if (word.length < term.length-limit) return limit+1;
    const target=word.slice(0,term.length+limit),length=target.length,large=limit+1;
    let previous=Array.from({length:length+1},(_,i)=>i),older=null;
    for(let i=1;i<=term.length;i++){
      const current=Array(length+1).fill(large);current[0]=i;let best=large;
      for(let j=Math.max(1,i-limit);j<=Math.min(length,i+limit);j++){
        let cost=Math.min(previous[j]+1,current[j-1]+1,previous[j-1]+(term[i-1]===target[j-1]?0:1));
        if(older&&j>1&&term[i-1]===target[j-2]&&term[i-2]===target[j-1])cost=Math.min(cost,older[j-2]+1);
        current[j]=cost;best=Math.min(best,cost);
      }
      if(best>limit)return large;
      older=previous;previous=current;
    }
    return Math.min(...previous.slice(Math.max(1,term.length-limit)));
  }
  function createSearchMatcher(query) {
    const normalized=normalizeSearch(query),terms=normalized.split(' ').filter(Boolean).map(t=>searchAliases[t]||t),cache=terms.map(()=>new Map());
    function score(item) {
      let distance=0;
      for(let i=0;i<terms.length;i++){
        const term=terms[i];if(item.text.includes(term))continue;
        // Never "correct" an LGD identifier or make short queries noisy.
        if(term.length<4||/\d/.test(term))return Infinity;
        const limit=term.length>=8?2:1;let best=limit+1;
        for(const word of item.words){
          if(!cache[i].has(word))cache[i].set(word,prefixDistance(term,word,limit));
          best=Math.min(best,cache[i].get(word));if(best===1)break;
        }
        if(best>limit)return Infinity;distance+=best;
      }
      return distance;
    }
    return {normalized,terms,score,test(value){
      const text=normalizeSearch(value),words=text.split(' ').filter(word=>word.length>=3&&!/\d/.test(word));
      return Number.isFinite(score({text,words}));
    }};
  }
  class Model {
    constructor(payload) {
      this.payload = payload;
      this.scope = payload.scope || {code:'0',name:'Centre',kind:'central'};
      const prefix = this.scope.code === '0' ? 'central' : 'state';
      this.datasets = {orgs:prefix+'_orgs',units:prefix+'_org_units',designations:prefix+'_org_designations',adminLevels:prefix+'_admin_depts',adminEntities:prefix+'_admin_dept_units'};
      const scoped = new Set([...Object.values(this.datasets),'org_unit_details','org_unit_coverage']);
      this.tables = {};
      for (const [name, table] of Object.entries(payload.tables)) {
        if ((name.startsWith('central_')||name.startsWith('state_'))&&!scoped.has(name)) continue;
        const stateIndex = table.fields.indexOf('state_code');
        const rows = scoped.has(name)&&stateIndex>=0 ? table.rows.filter(row=>row[stateIndex]===this.scope.code) : table.rows;
        this.tables[name] = rows.map(row => Object.fromEntries(table.fields.map((f, i) => [f, row[i]])));
      }
      this.nodes = new Map(); this.children = new Map(); this.parent = new Map();
      this.orgUnits = new Map(); this.details = new Map(); this.coverage = new Map();
      this.designations = new Map(); this.levelNames = new Map(); this.adminLevels = new Map();
      this.designationLevels = new Map(); this.designationEdges = [];
      this.adminEntities = new Map(); this.geo = new Map(); this.issues = [];
      this.edges = []; this.ownership = []; this.carriedUnits = new Map();
      this.rows(this.datasets.designations).forEach(r => {
        this.append(this.designations, r.organization_code, r);
        if (valid(r.organization_level_code)) this.append(this.levelNames, key(r.organization_code, r.organization_level_code), r.organization_level_name);
      });
      for (const r of this.rows(this.datasets.adminLevels)) this.adminLevels.set(r.administrative_unit_level_code, r);
      for (const r of this.rows(this.datasets.adminEntities)) this.adminEntities.set(key(r.administrative_unit_level_code, r.administrative_unit_code), r);
      for (const r of this.rows('states')) this.geo.set(key('1', r.state_code), r.state_name);
      for (const r of this.rows('districts')) this.geo.set(key('2', r.district_code), r.district_name);
      for (const r of this.rows('org_unit_details')) this.append(this.details, r.organization_unit_code, r);
      for (const r of this.rows('org_unit_coverage')) this.append(this.coverage, r.organization_unit_code, r);
      for (const r of payload.carried?.[this.datasets.units]?.records || []) this.carriedUnits.set(r.organization_unit_code, r.last_observed_on);
      for (const r of this.rows(this.datasets.orgs)) this.add({id: 'org:' + r.organization_code, kind: 'org', code: r.organization_code, name: r.organization_name, type: r.organization_type, raw: r, source: this.datasets.orgs, reference: false});
      for (const r of this.rows(this.datasets.orgs)) if (valid(r.parent_organization_code)) this.ensureOrg(r.parent_organization_code, r.parent_organization_name, r.parent_organization_type);
      for (const r of this.rows(this.datasets.units)) {
        this.ensureOrg(r.organization_code, r.organization_name);
        const n = {id: 'unit:' + r.organization_unit_code, kind: 'unit', code: r.organization_unit_code, name: r.organization_unit_name, type: 'Unit', raw: r, source: this.datasets.units, reference: false, org: r.organization_code};
        this.add(n); this.append(this.orgUnits, r.organization_code, n.id);
        this.ownership.push({source: 'org:' + r.organization_code, target: n.id, relation: 'organization membership', source_dataset: this.datasets.units});
      }
      // Additional report-only units remain references, never invented directory rows.
      for (const dataset of ['org_unit_details', 'org_unit_coverage']) for (const r of this.rows(dataset)) {
        this.ensureOrg(r.organization_code, r.organization_name);
        if (!this.nodes.has('unit:' + r.organization_unit_code)) {
          const n = {id: 'unit:' + r.organization_unit_code, kind: 'unit', code: r.organization_unit_code, name: r.organization_unit_name, type: 'Unit reference', raw: r, source: dataset, reference: true, org: r.organization_code};
          this.add(n); this.append(this.orgUnits, r.organization_code, n.id);
          this.ownership.push({source: 'org:' + r.organization_code, target: n.id, relation: 'organization reference', source_dataset: dataset});
        }
      }
      for (const r of this.rows(this.datasets.designations)) this.ensureOrg(r.organization_code, r.organization_name);
      for (const n of [...this.nodes.values()]) {
        const r = n.raw || {};
        if (n.kind === 'org' && valid(r.parent_organization_code)) this.connect('org:' + r.parent_organization_code, n.id, 'parent organization', this.datasets.orgs);
        if (n.kind === 'unit' && valid(r.parent_organization_unit_code)) {
          const pid = 'unit:' + r.parent_organization_unit_code;
          if (!this.nodes.has(pid)) {
            this.add({id: pid, code: r.parent_organization_unit_code, kind: 'unit', type: 'Parent reference', name: r.parent_organization_unit_name || 'Unlisted parent unit', reference: true, raw: {}, org: n.org});
            this.issues.push({kind: 'missing unit parent', unit: n.id, parent: pid});
          }
          this.connect(pid, n.id, 'parent unit', n.source);
        }
      }
      // Build a cycle-safe display forest without deleting any reported edges.
      for (const e of this.edges) {
        let cursor = e.source, cycle = cursor === e.target;
        const seen = new Set();
        while (!cycle && this.parent.has(cursor) && !seen.has(cursor)) {
          seen.add(cursor); cursor = this.parent.get(cursor); cycle = cursor === e.target;
        }
        if (cycle || this.parent.has(e.target)) { this.issues.push({kind: 'non-tree relationship', ...e}); continue; }
        this.parent.set(e.target, e.source); this.append(this.children, e.source, e.target);
      }
      // Place remaining unit roots directly under their organization by membership.
      // This display attachment does not create a reported parent-unit edge.
      for (const n of this.nodes.values()) {
        if (n.kind !== 'unit' || this.parent.has(n.id)) continue;
        const owner = 'org:' + n.org;
        if (this.nodes.has(owner)) this.attach(owner, n.id);
      }
      // A designation row associates a title with an organization and a level.
      // Display folders keep that association separate from organization/unit parents.
      for (const r of this.rows(this.datasets.designations)) {
        const folderId = 'designations:' + r.organization_code, levelId = designationLevelId(r);
        if (!this.nodes.has(folderId)) {
          this.add({id: folderId, kind: 'designation-group', name: 'Designation source records', type: 'Source catalogue', org: r.organization_code, count: 0, raw: {organization_code: r.organization_code}});
          this.attach('org:' + r.organization_code, folderId);
        }
        if (!this.nodes.has(levelId)) {
          this.add({id: levelId, kind: 'designation-level', name: r.organization_level_name || (valid(r.organization_level_code) ? 'Level ' + r.organization_level_code : 'Level not supplied'), type: 'Reported title level', code: r.organization_level_code, org: r.organization_code, count: 0, raw: {organization_code: r.organization_code, organization_level_code: r.organization_level_code, organization_level_name: r.organization_level_name}});
          this.attach(folderId, levelId);
          if (valid(r.organization_level_code)) this.append(this.designationLevels, key(r.organization_code, r.organization_level_code), levelId);
        }
        const n = {id: designationId(r), kind: 'designation', name: r.designation_name || 'Designation ' + r.designation_code, type: 'Designation', code: r.designation_code, org: r.organization_code, raw: r, source: this.datasets.designations};
        this.add(n); this.attach(levelId, n.id);
        this.node(folderId).count++; this.node(levelId).count++;
        this.designationEdges.push({source: 'org:' + n.org, target: n.id, relation: 'designation at organization level', organization_level_code: r.organization_level_code, organization_level_name: r.organization_level_name, source_dataset: n.source});
      }
      for (const ids of this.children.values()) ids.sort((a, b) => {
        const x = this.nodes.get(a), y = this.nodes.get(b);
        const rank = n => n.kind === 'org' ? 0 : n.kind === 'designation-group' ? 1 : n.kind === 'unit' ? 2 : 3;
        return rank(x) - rank(y) || compare(x, y);
      });
      this.roots = [...this.nodes.values()].filter(n => n.kind === 'org' && !this.parent.has(n.id)).sort(compare).map(n => n.id);
      for (const n of this.nodes.values()) if (n.kind === 'org') n.organizationDepth = this.ancestors(n.id).length - 1;
      this.organizations = [...this.nodes.values()].filter(n => n.kind === 'org' && !n.reference).sort((a, b) => a.organizationDepth - b.organizationDepth || compare(a, b));
      this.searchable = [...this.nodes.values()].filter(n => ['org','unit','designation'].includes(n.kind)).map(n => {
        const name=normalizeSearch(n.name),text=normalizeSearch(n.name+' '+n.code+' '+(n.org||'')+' '+(n.kind==='designation'?(n.raw.organization_name||'')+' '+(n.raw.organization_level_name||'')+' '+(n.raw.organization_level_code||''):''));
        return {node:n,name,text,words:[...new Set(text.split(' ').filter(word=>word.length>=3&&!/\d/.test(word)))]};
      });
    }
    rows(dataset) {return this.tables[dataset] || [];}
    add(n) {this.nodes.set(n.id, n);}
    attach(parent, child) {this.parent.set(child, parent); this.append(this.children, parent, child);}
    append(map, k, value) {if (!map.has(k)) map.set(k, []); map.get(k).push(value);}
    ensureOrg(code, name, type) {
      if (!valid(code)) return;
      const id = 'org:' + code;
      if (!this.nodes.has(id)) this.add({id, code, kind: 'org', type: type || 'Organization reference', name: name || 'Unlisted organization ' + code, reference: true, raw: {organization_code: code}});
    }
    connect(source, target, relation, dataset) {this.edges.push({source, target, relation, source_dataset: dataset});}
    node(id) {
      if(this.nodes.has(id))return this.nodes.get(id);
      if(typeof id!=='string'||!id.startsWith('unit-designation:'))return;
      // A title can apply at many offices. Resolve its display occurrence lazily,
      // retaining the original association ID instead of duplicating source rows.
      try {
        const [unitId,associationId]=JSON.parse(id.slice('unit-designation:'.length));
        const unit=this.nodes.get(unitId),title=this.nodes.get(associationId);
        if(unit?.kind!=='unit'||title?.kind!=='designation'||!valid(unit.raw.organization_level_code)||unit.org!==title.org||unit.raw.organization_level_code!==title.raw.organization_level_code)return;
        return {...title,id,unitId,associationId};
      } catch {return;}
    }
    parentId(id) {return this.node(id)?.unitId || this.parent.get(id);}
    childIds(id, includeUnits = true, includeDesignations = true) {return (this.children.get(id) || []).filter(k => {const kind=this.node(k).kind;return (includeUnits || kind !== 'unit') && (includeDesignations || !['designation','designation-group','designation-level'].includes(kind));});}
    designationLevelIds(n) {return n.kind === 'unit' && valid(n.raw.organization_level_code) ? this.designationLevels.get(key(n.org, n.raw.organization_level_code)) || [] : [];}
    unitDesignationIds(n) {
      return this.designationLevelIds(n).flatMap(id=>this.children.get(id)||[]).sort((a,b)=>compare(this.node(a),this.node(b))).map(id=>unitDesignationId(n.id,id));
    }
    displayChildIds(id, includeUnits=true, includeDesignations=true) {
      const n=this.node(id);
      if(!n)return [];
      const children=this.childIds(id,includeUnits,includeDesignations).filter(child=>n.kind!=='org'||this.node(child).kind!=='designation-group');
      // Surface member offices before child organizations in the display.
      if(n.kind==='org')children.sort((a,b)=>Number(this.node(b).kind==='unit')-Number(this.node(a).kind==='unit'));
      // Unit titles are a separate association, with their own expansion control.
      return children;
    }
    unitsForDesignation(n) {
      return n.kind==='designation'&&valid(n.raw.organization_level_code) ? (this.orgUnits.get(n.org)||[]).filter(id=>this.node(id).raw.organization_level_code===n.raw.organization_level_code) : [];
    }
    designationRows(n) {
      if (n.kind === 'designation') return [n.raw];
      if (n.kind === 'designation-level') return (this.children.get(n.id) || []).map(id => this.node(id).raw);
      const rows=this.designations.get(n.kind === 'org' ? n.code : n.org) || [];
      return n.kind === 'unit' ? rows.filter(r => valid(n.raw.organization_level_code) && r.organization_level_code === n.raw.organization_level_code) : rows;
    }
    ancestors(id) {const ids = [], seen = new Set(); while (id && !seen.has(id)) {seen.add(id); ids.unshift(id); id = this.parentId(id);} return ids;}
    detailsFor(n) {return (this.details.get(n.code) || []).filter(r => r.organization_code === n.org);}
    coverageFor(n) {return (this.coverage.get(n.code) || []).filter(r => r.organization_code === n.org);}
    coverageClaimsFor(n) {return this.coverageFor(n).filter(r => r.coverage_details_reported === 'true');}
    location(n) {
      const r = n.raw, admin = this.adminEntities.get(key(r.entity_type, r.entity_code));
      const matching = this.detailsFor(n).filter(d => d.entity_type === r.entity_type && d.entity_code === r.entity_code);
      const reportedNames = [...new Set(matching.map(d => d.entity_name).filter(Boolean))];
      const labels = [...new Set(matching.map(d => d.entity_type_name).filter(Boolean))];
      const level = this.adminLevels.get(r.entity_type);
      const typeName = labels.join(' / ') || level?.administrative_unit_level_name || ({'1':'State','2':'District','3':'Subdistrict','4':'Village','5':'Block'}[r.entity_type]) || '';
      const resolved = admin?.administrative_unit_name || this.geo.get(key(r.entity_type, r.entity_code)) || '';
      return {type: r.entity_type || '', code: r.entity_code || '', typeName, resolved, reportedNames, level, admin, details: matching, unlabelled: !typeName};
    }
    search(query, kind = 'all') {
      const matcher=createSearchMatcher(query),{normalized,terms}=matcher;
      if (!terms.length) return [];
      const rank={org:0,unit:1,designation:2},matches=[];
      for(const item of this.searchable){
        if(kind!=='all'&&item.node.kind!==kind)continue;
        const distance=matcher.score(item);
        if(Number.isFinite(distance))matches.push({node:item.node,score:item.node.code===normalized?0:item.name===normalized?1:distance?3+distance:2});
      }
      return matches.sort((a,b)=>a.score-b.score||rank[a.node.kind]-rank[b.node.kind]||
        (a.node.kind==='org'?a.node.organizationDepth-b.node.organizationDepth:0)||compare(a.node,b.node)).map(x=>x.node);
    }
  }
  const api = {Model, key, valid, designationId, designationLevelId, unitDesignationId, createSearchMatcher};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.LGDGraph = api;
})(globalThis);
