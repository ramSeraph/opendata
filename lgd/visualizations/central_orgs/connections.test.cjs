const {test} = require('node:test');
const assert = require('node:assert/strict');
const {ConnectionIndex} = require('./connections.js');

function fan(count) {
  const nodes = new Map([['parent', {x:0,y:0}]]), edges = [];
  for (let i=0;i<count;i++) {
    nodes.set('child:'+i, {x:355,y:i*162});
    edges.push({source:'parent',target:'child:'+i,label:'organization membership'});
  }
  return {nodes,edges,index:new ConnectionIndex(edges,nodes,270,138)};
}
function clipped(segments, box) {
  for (const s of segments) {
    assert(s.x1>=box.xmin&&s.x2<=box.xmax&&s.y1>=box.ymin&&s.y2<=box.ymax);
  }
}

test('a large organization paints a shared trunk and only the visible child branches',()=>{
  const {index,edges}=fan(30000), before=JSON.stringify(edges);
  for (const y of [0,162*15000,162*29994]) {
    const box={xmin:250,xmax:400,ymin:y,ymax:y+900};
    const result=index.query(box);
    assert.equal(result.groupsVisited,1);
    assert(result.targetsVisited<=6);
    assert(result.branches.length>=5&&result.branches.length<=6);
    assert(result.segments.length<=8);
    assert(result.branches.every(b=>b.y>=box.ymin&&b.y<=box.ymax));
    clipped(result.segments,box);
  }
  assert.equal(JSON.stringify(edges),before,'Rendering must retain every original relationship');
});

test('parent connections remain visible when child cards are beyond the right edge',()=>{
  const {index}=fan(10), box={xmin:270,xmax:290,ymin:40,ymax:90};
  const result=index.query(box);
  assert.equal(result.branches.length,0);
  assert.deepEqual(result.segments,[{x1:270,y1:69,x2:290,y2:69,style:'association'}]);
});

test('a trunk crossing the viewport survives when both endpoint cards are offscreen',()=>{
  const nodes=new Map([['parent',{x:0,y:0}],['child',{x:355,y:16200}]]);
  const index=new ConnectionIndex([{source:'parent',target:'child',label:'parent unit'}],nodes,270,138);
  const box={xmin:300,xmax:340,ymin:500,ymax:800}, result=index.query(box);
  assert.deepEqual(result.branches,[]);
  assert.deepEqual(result.segments,[{x1:320.5,y1:500,x2:320.5,y2:800,style:'parent'}]);
  clipped(result.segments,box);
});

test('viewport queries exclude unrelated parent branches and graph columns',()=>{
  const nodes=new Map(),edges=[];
  for(let i=0;i<10000;i++) {
    nodes.set('p'+i,{x:0,y:i*1000});nodes.set('c'+i,{x:355,y:i*1000+200});
    edges.push({source:'p'+i,target:'c'+i,label:'parent unit'});
  }
  const index=new ConnectionIndex(edges,nodes,270,138);
  const result=index.query({xmin:270,xmax:355,ymin:5000000,ymax:5000500});
  assert.equal(result.groupsVisited,1);assert.equal(result.targetsVisited,1);
  assert.equal(result.branches[0].edge.target,'c5000');
  assert.equal(index.query({xmin:700,xmax:800,ymin:0,ymax:10000000}).groupsVisited,0);
});

test('membership, parent and designation associations keep separate styles and source edges',()=>{
  const nodes=new Map([['parent',{x:0,y:0}],['a',{x:355,y:0}],['b',{x:355,y:162}],['c',{x:355,y:324}]]);
  const edges=[{source:'parent',target:'a',label:'organization membership'},
    {source:'parent',target:'b',label:'parent organization'},
    {source:'parent',target:'c',label:'designation for this unit’s level',association_id:'title:1'}];
  const index=new ConnectionIndex(edges,nodes,270,138);
  const result=index.query({xmin:0,xmax:1000,ymin:0,ymax:1000});
  assert.deepEqual(result.branches.map(b=>b.style).sort(),['association','parent','title']);
  assert.deepEqual(new Set(result.branches.map(b=>b.edge)),new Set(edges));
});
