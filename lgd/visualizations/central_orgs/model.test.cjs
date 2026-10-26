const {test} = require('node:test');
const assert = require('node:assert/strict');
const {Model,designationId,designationLevelId,unitDesignationId} = require('./model.js');

function payload(tables) {
  return {tables: Object.fromEntries(Object.entries(tables).map(([name,rows])=>{
    const fields=[...new Set(rows.flatMap(Object.keys))];
    return [name,{fields,rows:rows.map(r=>fields.map(f=>r[f]??''))}];
  })),sources:{},carried:{}};
}
const org=(code,parent='')=>({organization_code:code,organization_name:'Organization '+code,organization_type:'Department',parent_organization_code:parent,parent_organization_name:'Parent '+parent});
const unit=(code,parent='',level='10')=>({organization_unit_code:code,organization_unit_name:'Unit '+code,organization_code:'1',organization_name:'Organization 1',parent_organization_unit_code:parent,organization_level_code:level,entity_type:'1150',entity_code:'51466'});

test('fuzzy names support typos, transpositions, prefixes and reordered words without changing codes',()=>{
  const m=new Model(payload({central_orgs:[
    {...org('1066'),organization_name:'Department of Telecommunication'},
    {...org('1149'),organization_name:'Department of Posts'},
    {...org('1000'),organization_name:'Kurnool'},
    {...org('1001'),organization_name:'Kurnol'},
  ],central_org_units:[{...unit('1991846'),organization_unit_name:'Postal Circles (Postal Region–Kurnool)'}],
  central_org_designations:[{designation_code:'5082',designation_name:'Deputy General Manager',organization_code:'1066',organization_name:'Department of Telecommunication',organization_level_code:'2240'}]}));
  assert.equal(m.search('depatment telecomunication','org')[0].code,'1066');
  assert.equal(m.search('dept telecommnuication','org')[0].code,'1066');
  assert.equal(m.search('telecm dept','org')[0].code,'1066');
  assert.equal(m.search('kurnol postal','unit')[0].code,'1991846');
  assert.equal(m.search('KURNOL','org')[0].code,'1001','An exact name precedes a fuzzy spelling');
  assert.equal(m.search(' 1066 ')[0].code,'1066','Exact codes precede records mentioning the same organization');
  assert.deepEqual(m.search('1991847'),[],'One digit wrong must not match a nearby unit code');
  assert.deepEqual(m.search('1991847 kurnol'),[]);
  assert.equal(m.search('deputy genreal','designation')[0].code,'5082');
  assert.deepEqual(m.search(''),[]);
});

test('Centre and states isolate identical codes, joins and source provenance',()=>{
  const rows={central_orgs:[{...org('1'),state_code:'0',organization_name:'Central organization'}],central_org_units:[{...unit('1'),state_code:'0'}]};
  for(const code of ['28','33']){
    const add=(name,row)=>(rows[name]??=[]).push({...row,state_code:code});
    add('state_orgs',{...org('1'),organization_name:'Organization in '+code});
    add('state_org_units',{...unit('1'),organization_unit_name:'Office in '+code});
    add('state_org_designations',{designation_code:'7',designation_name:'Officer in '+code,organization_code:'1',organization_level_code:'10',organization_level_name:'Head Office'});
    add('state_admin_depts',{administrative_unit_level_code:'1150',administrative_unit_level_name:'Region in '+code});
    add('state_admin_dept_units',{administrative_unit_level_code:'1150',administrative_unit_code:'51466',administrative_unit_name:'Entity in '+code});
    add('org_unit_details',{...unit('1'),entity_name:'Entity in '+code});
    add('org_unit_coverage',{organization_code:'1',organization_unit_code:'1',covered_entity_code:'33',covered_entity_type:'State',coverage_details_reported:'true'});
  }
  rows.org_unit_details.push({...unit('1'),state_code:'0'});
  rows.org_unit_coverage.push({organization_code:'1',organization_unit_code:'1',state_code:'0',covered_entity_code:'28',covered_entity_type:'State'});
  rows.states=[{state_code:'28',state_name:'Andhra Pradesh'},{state_code:'33',state_name:'Tamil Nadu'}];
  for(const code of ['0','28','33']){
    const p=payload(rows);p.scope={code,name:code,kind:code==='0'?'central':'state'};
    const m=new Model(p),u=m.node('unit:1');
    assert.equal(m.organizations.length,1);assert.equal(m.rows(m.datasets.units).length,1);
    assert.equal(m.detailsFor(u).length,1);assert.equal(m.coverageFor(u).length,1);
    assert.equal(m.detailsFor(u)[0].state_code,code);assert.equal(m.coverageFor(u)[0].state_code,code);
    assert.equal(m.geo.get(JSON.stringify(['1','33'])),'Tamil Nadu','Geographic registers must remain complete');
    if(code==='0'){
      assert.equal(m.node('org:1').name,'Central organization');
      assert.equal(m.rows('state_orgs').length,0);assert.equal(m.unitDesignationIds(u).length,0);
    }else{
      assert.equal(m.node('org:1').name,'Organization in '+code);
      assert.equal(m.rows('central_orgs').length,0);
      assert.equal(m.location(u).resolved,'Entity in '+code);assert.equal(m.location(u).typeName,'Region in '+code);
      assert.equal(m.coverageFor(u)[0].covered_entity_code,'33','Coverage target must not determine the owning state');
      const title=m.node(m.unitDesignationIds(u)[0]);
      assert.equal(title.name,'Officer in '+code);assert.equal(title.source,'state_org_designations');
      assert.equal(u.source,'state_org_units');assert.equal(m.ownership[0].source_dataset,'state_org_units');
      assert.equal(m.search('Central organization').length,0);
      assert.equal(m.search('Office in '+(code==='28'?'33':'28')).length,0);
    }
  }
});

test('a state with no records remains empty rather than falling back to Centre',()=>{
  const p=payload({central_orgs:[org('1')],central_org_units:[unit('1')]});p.scope={code:'31',name:'Lakshadweep',kind:'state'};
  const m=new Model(p);
  assert.deepEqual(m.roots,[]);assert.deepEqual(m.organizations,[]);assert.deepEqual(m.search('Unit'),[]);
});

test('organization membership and unit parent are distinct, with separate ID namespaces',()=>{
  const m=new Model(payload({central_orgs:[org('1','8')],central_org_units:[unit('1'),unit('2','1')]}));
  assert.equal(m.node('org:8').reference,true);
  assert.equal(m.node('org:1').reference,false);
  assert.equal(m.parent.get('org:1'),'org:8');
  assert.equal(m.parent.get('unit:2'),'unit:1');
  assert.equal(m.ownership.find(e=>e.target==='unit:2').source,'org:1');
  assert.equal(m.edges.find(e=>e.target==='unit:2').relation,'parent unit');
  assert.notEqual(m.node('org:1'),m.node('unit:1'));
});
test('root units attach directly to their organization while reported parent units stay intact',()=>{
  const units=[unit('1'),unit('2'),unit('3'),unit('4'),unit('5','','20'),unit('6','1'),unit('7','999'),{...unit('8'),organization_code:'2'}];
  for (const prefix of ['central','state']) {
    const p=payload({[prefix+'_orgs']:[org('1'),org('2')],[prefix+'_org_units']:units});
    p.scope={code:prefix==='central'?'0':'28',name:prefix};
    const m=new Model(p);
    assert.equal([...m.nodes.values()].some(n=>n.kind==='group'),false);
    assert.deepEqual(m.displayChildIds('org:1'),['unit:1','unit:2','unit:3','unit:4','unit:5','unit:999']);
    assert.deepEqual(m.displayChildIds('org:2'),['unit:8']);
    assert.equal(m.parentId('unit:6'),'unit:1');
    assert.equal(m.parentId('unit:7'),'unit:999');
    assert.equal(m.node('unit:999').reference,true);
    assert.deepEqual(m.edges.map(e=>[e.source,e.target,e.relation]),[
      ['unit:1','unit:6','parent unit'],['unit:999','unit:7','parent unit']
    ]);
    assert.equal(m.ownership.length,units.length);
    assert.deepEqual(m.rows(prefix+'_org_units'),units,'Source rows must stay unchanged');
    assert.deepEqual(m.childIds('org:1',false),[]);
  }
});
test('location lookup uses both entity type and code; mismatched details remain raw',()=>{
  const details=[{...unit('1'),state_code:'0',entity_type:'2',entity_code:'51466',entity_type_name:'District',entity_name:'Wrong entity'}];
  const m=new Model(payload({central_orgs:[org('1')],central_org_units:[unit('1')],org_unit_details:details,
    central_admin_depts:[{administrative_unit_level_code:'1150',administrative_unit_level_name:'Postal Circle'}],
    central_admin_dept_units:[{administrative_unit_level_code:'1150',administrative_unit_code:'51466',administrative_unit_name:'Andhra Pradesh'},
      {administrative_unit_level_code:'1151',administrative_unit_code:'51466',administrative_unit_name:'Different region'}]}));
  const location=m.location(m.node('unit:1'));
  assert.equal(location.resolved,'Andhra Pradesh');assert.equal(location.typeName,'Postal Circle');
  assert.deepEqual(location.reportedNames,[]);assert.equal(m.detailsFor(m.node('unit:1')).length,1);
});
test('coverage multiplicity and designation-level associations are preserved',()=>{
  const claim={organization_unit_code:'1',organization_code:'1',state_code:'0',covered_entity_code:'9',covered_entity_type:'District',coverage_type:'F',coverage_details_reported:'true'};
  const m=new Model(payload({central_orgs:[org('1')],central_org_units:[unit('1')],org_unit_coverage:[claim,claim],central_org_designations:[
    {organization_code:'1',designation_code:'7',organization_level_code:'10',organization_level_name:'Circle'},
    {organization_code:'1',designation_code:'7',organization_level_code:'',organization_level_name:'Circle'}]}));
  assert.equal(m.coverageFor(m.node('unit:1')).length,2);
  assert.equal(m.designations.get('1').length,2);
});
test('cycles are reported while all original edges remain available',()=>{
  const m=new Model(payload({central_orgs:[org('1')],central_org_units:[unit('1','2'),unit('2','1')]}));
  assert.equal(m.edges.length,2);assert.equal(m.issues.length,1);
  const path=m.ancestors('unit:1');assert.equal(new Set(path).size,path.length);
});
test('designation graph preserves organization and level associations, including blank codes',()=>{
  const title={designation_code:'7',designation_name:'Postmaster',organization_code:'1',organization_name:'Organization 1',organization_level_code:'10',organization_level_name:'Head Office'};
  const blank={...title,organization_level_code:''},otherOrg={...title,organization_code:'2'},otherName={...title,organization_level_name:'Another supplied name'};
  const m=new Model(payload({central_orgs:[org('1'),org('2')],central_org_units:[unit('1'),unit('2','','')],central_org_designations:[title,blank,otherOrg,otherName]}));
  assert.equal([...m.nodes.values()].filter(n=>n.kind==='designation').length,4);
  assert.equal(m.designationEdges.length,4);
  assert.equal(m.parent.get(designationId(title)),designationLevelId(title));
  assert.equal(m.parent.get(designationLevelId(title)),'designations:1');
  assert.equal(m.parent.get('designations:1'),'org:1');
  assert.deepEqual(m.designationRows(m.node('unit:1')),[title,otherName]);
  assert.deepEqual(m.designationLevelIds(m.node('unit:1')),[designationLevelId(title),designationLevelId(otherName)]);
  assert.deepEqual(m.designationLevelIds(m.node('unit:2')),[]);
  assert.deepEqual(m.designationRows(m.node('unit:2')),[]);
  assert.deepEqual(m.designationRows(m.node(designationLevelId(blank))),[blank]);
  assert.equal(m.search('Postmaster','designation').length,4);
  assert.deepEqual(m.childIds('org:1',false),['designations:1']);
  assert.deepEqual(m.childIds('org:1',false,false),[]);
  assert(!m.edges.some(e=>e.target.startsWith('designation')),'Title grouping must not create parent-organization/unit source edges');
});
test('organization listings sort by parent-chain depth and then name, including reference parents',()=>{
  const m=new Model(payload({central_orgs:[
    {...org('3','2'),organization_name:'A Grandchild'},
    {...org('2','1'),organization_name:'Z Child'},
    {...org('5','8'),organization_name:'A Child of an unlisted parent'},
    {...org('4'),organization_name:'A Root'},
    {...org('1'),organization_name:'Z Root'}
  ]}));
  assert.deepEqual(m.organizations.map(n=>n.code),['4','1','5','2','3']);
  assert.deepEqual(m.organizations.map(n=>n.organizationDepth),[0,0,1,1,2]);
  assert.equal(m.node('org:8').organizationDepth,0);
  assert.deepEqual(m.search('Child','org').map(n=>n.code),['5','2','3']);
});
test('unit designations are separate from ordinary children and preserve source identity',()=>{
  const title={designation_code:'7',designation_name:'Officer',organization_code:'1',organization_level_code:'10',organization_level_name:'Head Office'};
  const blank={...title,organization_level_code:''},otherOrg={...title,organization_code:'2'};
  const m=new Model(payload({central_orgs:[org('1'),org('2')],central_org_units:[unit('1'),unit('2'),unit('3','',''),{...unit('4'),organization_code:'2'}],central_org_designations:[title,blank,otherOrg]}));
  const first=unitDesignationId('unit:1',designationId(title)),second=unitDesignationId('unit:2',designationId(title));
  assert.deepEqual(m.displayChildIds('unit:1'),[]);
  assert.deepEqual(m.displayChildIds('unit:2'),[]);
  assert.deepEqual(m.unitDesignationIds(m.node('unit:1')),[first]);
  assert.deepEqual(m.unitDesignationIds(m.node('unit:2')),[second]);
  assert.equal(m.node(first).associationId,m.node(second).associationId);
  assert.deepEqual(m.node(first).raw,title);
  assert.equal(m.node(first).unitId,'unit:1');
  assert.equal(m.parentId(first),'unit:1');
  assert.deepEqual(m.ancestors(first),['org:1','unit:1',first]);
  assert.deepEqual(m.displayChildIds('unit:1',true,false),[]);
  assert.deepEqual(m.displayChildIds('unit:3'),[]);
  assert.equal(m.node(unitDesignationId('unit:1',designationId(blank))),undefined);
  assert.equal(m.node(unitDesignationId('unit:4',designationId(title))),undefined);
  assert(!m.displayChildIds('org:1').includes('designations:1'));
  assert(m.node('designations:1'),'Source catalogue must remain available independently');
  assert.equal([...m.nodes.values()].filter(n=>n.kind==='designation').length,3);
  assert.equal(m.edges.length,0,'A derived title association must not create a reported parent edge');
  assert.deepEqual(m.unitsForDesignation(m.node(first)),['unit:1','unit:2']);
});

test('unit children, titles, location and coverage remain independent relationships',()=>{
  const title={designation_code:'7',designation_name:'Officer',organization_code:'1',organization_level_code:'10',organization_level_name:'Head Office'};
  const m=new Model(payload({central_orgs:[org('1')],central_org_units:[unit('1'),unit('2','1')],central_org_designations:[title],org_unit_coverage:[{organization_unit_code:'1',organization_code:'1',covered_entity_code:'123'}]}));
  assert.deepEqual(m.displayChildIds('unit:1'),['unit:2']);
  assert.deepEqual(m.displayChildIds('unit:1',true,false),['unit:2']);
  assert.deepEqual(m.displayChildIds('unit:1',false,true),[]);
  assert.equal(m.unitDesignationIds(m.node('unit:1')).length,1);
  assert.equal(m.location(m.node('unit:1')).code,'51466');
  assert.equal(m.coverageFor(m.node('unit:1')).length,1);
  assert.equal(m.edges.length,1);assert.equal(m.edges[0].relation,'parent unit');
});

test('coverage counts omit no-details placeholders without discarding unlabelled claims or source rows',()=>{
  const base={organization_unit_code:'1',organization_code:'1',state_code:'0'};
  const placeholder={...base,coverage_details_reported:'false',covered_entity_code:'',covered_entity_name:'',covered_entity_type:''};
  const unlabelled={...base,coverage_details_reported:'true',covered_entity_code:'123',covered_entity_name:'',covered_entity_type:'',coverage_type:'P'};
  const named={...base,coverage_details_reported:'true',covered_entity_code:'28',covered_entity_name:'Andhra Pradesh',covered_entity_type:'State',coverage_type:'F'};
  const m=new Model(payload({central_orgs:[org('1')],central_org_units:[unit('1'),unit('2')],org_unit_coverage:[placeholder,unlabelled,named,{...placeholder,organization_unit_code:'2'}]}));
  assert.deepEqual(m.coverageClaimsFor(m.node('unit:1')).map(r=>r.covered_entity_code),['123','28']);
  assert.equal(m.coverageFor(m.node('unit:1')).length,3);
  assert.deepEqual(m.coverageClaimsFor(m.node('unit:2')),[]);
  assert.equal(m.coverageFor(m.node('unit:2')).length,1);
});
