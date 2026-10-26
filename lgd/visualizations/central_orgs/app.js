(async function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => Number(n || 0).toLocaleString('en-IN');
  const nice = s => s ? new Date(s + 'T00:00:00Z').toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}) : 'Not supplied';
  const sourceUse = {central_orgs:'Organization names, types and reported parents',central_org_units:'Office membership, parent offices and typed location references',central_org_designations:'Titles associated with an organization and its levels; not staff assignments',central_admin_depts:'Names and metadata for administrative entity types',central_admin_dept_units:'Names of individual administrative entities',org_unit_details:'Additional location names, parent claims and office details',org_unit_coverage:'Separate coverage claims, including full/partial and no-details rows',states:'Independent state-name lookup',districts:'Independent district-name lookup'};
  for(const [name,use] of Object.entries(sourceUse))if(name.startsWith('central_'))sourceUse[name.replace('central_','state_')]=use;
  const W = 270, H = 138, DX = 355, DY = 162;
  const freshState = code => ({scope:code,focus:code==='0'?'unit:1991823':null,selected:code==='0'?'unit:1991823':null,open:new Set(),titlesOpen:new Set(),childrenScroll:0,reference:null,includeUnits:true,includeDesignations:true,labels:true,tab:'meaning',searchKind:'all',coveragePage:0,coverageQuery:'',rolesPage:0});
  const state = freshState('0');
  let model, payload, view = {nodes:[],edges:[]}, zoom = 1, tx = 30, ty = 30, width = 800, height = 600, raf = 0;
  const canvas = $('graph'), ctx = canvas.getContext('2d');
  let bytes, loadingScope=false, loadSequence=0, referenceContext=null;
  const scopeIndex=JSON.parse($('scope-index').textContent), scopeMap=new Map(scopeIndex.scopes.map(s=>[s.code,s]));
  const savedViews=new Map(), pendingScopes=new Map();
  $('scope-select').innerHTML=scopeIndex.scopes.map(s=>'<option value="'+esc(s.code)+'">'+esc(s.name)+'</option>').join('');
  LGDGraph.receiveScope=(code,encoded)=>pendingScopes.get(code)?.resolve(encoded);
  function scopeData(meta){
    if(meta.code==='0'&&$('packed-data').textContent.trim())return Promise.resolve($('packed-data').textContent.trim());
    if(pendingScopes.has(meta.code))return pendingScopes.get(meta.code).promise;
    const script=document.createElement('script');
    const item={};item.promise=new Promise((resolve,reject)=>{item.resolve=resolve;item.reject=reject;});
    pendingScopes.set(meta.code,item);
    const timeout=setTimeout(()=>item.reject(new Error('Loading '+meta.name+' timed out. Keep the scopes folder beside index.html.')),45000);
    script.src=new URL(meta.file+'?v='+meta.sha256.slice(0,16),location.href).href;
    script.onerror=()=>item.reject(new Error('Could not load '+meta.name+'. Keep the scopes folder beside index.html.'));
    script.onload=()=>item.reject(new Error('The data file did not supply '+meta.name+'. Rebuild the explorer folder.'));
    document.head.appendChild(script);
    return item.promise.finally(()=>{clearTimeout(timeout);script.remove();pendingScopes.delete(meta.code);});
  }
  function rememberScope(){if(!model)return;savedViews.set(state.scope,{state:{...state,open:new Set(state.open),titlesOpen:new Set(state.titlesOpen),reference:state.reference?{...state.reference}:null},query:$('search').value,camera:{zoom,tx,ty,width,height},navScroll:document.querySelector('.navigator').scrollTop,listScroll:$('organizations').scrollTop});}
  function scopeHeader(){
    const dates=[...new Set(Object.values(payload.sources).filter(s=>s.rows).map(s=>s.date))].sort();
    $('dateline').textContent=model.scope.name+' · Latest snapshots · '+nice(dates[0])+' – '+nice(dates.at(-1))+' · No history';
    $('totals').textContent=fmt(model.rows(model.datasets.orgs).length)+' organizations / '+fmt(model.rows(model.datasets.units).length)+' units / '+fmt(model.rows(model.datasets.designations).length)+' title associations';
    $('scope-select').value=state.scope;
    $('scope-status').className='';$('scope-status').textContent=fmt(model.rows(model.datasets.orgs).length)+' organizations · '+fmt(model.rows(model.datasets.units).length)+' units';
    document.title='LGD — '+model.scope.name+' organizations';
  }
  function renderExamples(){
    let examples;
    if(state.scope==='0')examples=[['org:1149','Department of Posts','Organization → offices → postal entities'],['org:1066','Department of Telecommunication','Organization, unit and title catalogue'],['unit:1991926','Vijayawada postal division','Office hierarchy, location and coverage'],['org:2143','Rubber Board','Regional offices and field stations']];
    else examples=[...model.organizations].filter(n=>model.orgUnits.has(n.code)).sort((a,b)=>model.orgUnits.get(b.code).length-model.orgUnits.get(a.code).length).slice(0,3).map(n=>[n.id,n.name,fmt(model.orgUnits.get(n.code).length)+' member units']);
    $('examples').innerHTML='<span class="eyebrow">Explore '+esc(model.scope.name)+'</span>'+examples.filter(([id])=>model.node(id)).map(([id,name,detail])=>'<button data-focus="'+esc(id)+'"><b>'+esc(name)+'</b><small>'+esc(detail)+'</small></button>').join('');
  }
  async function changeScope(code,initialHash=null){
    const meta=scopeMap.get(code);if(!meta)return false;
    if(!loadingScope&&model&&code===state.scope)return true;
    if(!loadingScope)rememberScope();
    clearTimeout(timer);clearTimeout(coverageTimer);
    const sequence=++loadSequence;loadingScope=true;referenceContext=null;$('reference-panel').hidden=true;document.body.classList.add('scope-busy');
    $('scope-select').value=code;$('scope-status').className='';$('scope-status').textContent='Loading '+meta.name+'…';
    $('loading').hidden=false;$('loading').innerHTML='<div class="spinner"></div><strong>Opening '+esc(meta.name)+'</strong><span>Loading this selection’s organizations, units and related records.</span>';
    try{
      const encoded=await scopeData(meta);if(sequence!==loadSequence)return false;
      const nextBytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
      const text=await new Response(new Blob([nextBytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
      if(sequence!==loadSequence)return false;
      const nextPayload=JSON.parse(text);if(nextPayload.scope?.code!==code)throw new Error('Data selection does not match '+meta.name+'.');
      await new Promise(resolve=>requestAnimationFrame(resolve));if(sequence!==loadSequence)return false;
      const nextModel=new LGDGraph.Model(nextPayload),saved=savedViews.get(code);
      model=nextModel;payload=nextPayload;bytes=nextBytes;
      Object.assign(state,freshState(code),saved?.state||{},{scope:code});
      if(initialHash?.has('focus'))state.focus=initialHash.get('focus')||null;
      if(initialHash?.get('selected'))state.selected=initialHash.get('selected');
      if(state.focus&&!model.node(state.focus))state.focus=null;
      if(!model.node(state.selected))state.selected=state.focus||model.roots[0]||null;
      if(!saved){
        if(state.focus)state.open.add(state.focus);
        const selected=model.node(state.selected);if(selected&&isTitle(selected)&&!selected.unitId&&!isTitle(model.node(state.focus)||{}))state.focus='designations:'+selected.org;
        openPath(state.selected);
      }
      $('search').value=saved?.query||'';
      $('show-units').checked=state.includeUnits;$('show-designations').checked=state.includeDesignations;$('show-labels').checked=state.labels;
      document.querySelectorAll('#search-kinds button').forEach(b=>b.classList.toggle('active',b.dataset.kind===state.searchKind));
      scopeHeader();renderExamples();renderOrganizations();search();
      const box=$('canvas-wrap').getBoundingClientRect();width=box.width;height=box.height;
      if(saved){({zoom,tx,ty}=saved.camera);tx+=(width-saved.camera.width)/2;ty+=(height-saved.camera.height)/2;refresh(false);}
      else refresh();
      inspect();saveHash();$('hover-tip').hidden=true;
      document.querySelector('.navigator').scrollTop=saved?.navScroll||0;$('organizations').scrollTop=saved?.listScroll||0;
      return true;
    }catch(error){
      if(sequence===loadSequence){$('scope-select').value=model?state.scope:code;$('scope-status').className='error';$('scope-status').textContent=error.message;if(!model)$('loading').innerHTML='<strong>Could not open the graph</strong><span>'+esc(error.message)+'</span><span>Use a current browser and keep the explorer folder together.</span>';}
      return false;
    }finally{if(sequence===loadSequence){loadingScope=false;document.body.classList.remove('scope-busy');if(model){$('loading').hidden=true;requestDraw();}}}
  }

  function node(id) {return model.node(id) || view.nodes.find(n => n.id === id);}
  function childIds(id) {return model.displayChildIds(id,state.includeUnits,state.includeDesignations);}
  function isTitle(n) {return ['designation','designation-group','designation-level'].includes(n.kind);}
  function titleLevelLabel(n) {return n.raw.organization_level_name || (LGDGraph.valid(n.raw.organization_level_code)?'Level '+n.raw.organization_level_code:'');}
  function edgeLabel(parent,child) {
    if (child.unitId) return 'designation for this unit’s level';
    if (child.kind==='designation-group') return 'designation associations';
    if (child.kind==='designation-level') return 'reported title level';
    if (child.kind==='designation') return 'title at this level';
    if (parent.kind==='group') return 'no parent unit reported';
    if (child.kind==='group') return 'members, grouped by level';
    if (parent.kind==='org' && child.kind==='unit') return 'organization membership';
    return child.kind==='org' ? 'parent organization' : 'parent unit';
  }
  function hasLocation(n){return LGDGraph.valid(n.raw.entity_type)&&LGDGraph.valid(n.raw.entity_code);}
  function titleCount(n){return n.kind==='unit'?model.designationLevelIds(n).reduce((sum,id)=>sum+(model.children.get(id)?.length||0),0):0;}
  function openPath(id){const path=model.ancestors(id);for(let i=0;i<path.length-1;i++){if(model.node(path[i+1])?.unitId)state.titlesOpen.add(path[i]);else state.open.add(path[i]);}}
  function buildView() {
    const nodes=[],edges=[],byId=new Map(),incoming=new Map();let leaf=0;
    const roots=state.focus&&model.node(state.focus)?[state.focus]:model.roots;
    const stack=roots.slice().reverse().map(id=>({id,depth:0}));
    // Iterative layout has no child-page, node-count or depth cutoff.
    while(stack.length){
      const frame=stack.pop();
      if(frame.finish){
        const kids=frame.ids.map(id=>byId.get(id)).filter(Boolean),v=frame.node;
        const firstOffice=v.kind==='org'&&kids.find(n=>n.kind==='unit');
        v.y=firstOffice?firstOffice.y:kids.length?(kids[0].y+kids.at(-1).y)/2:leaf++*DY;
        continue;
      }
      if(byId.has(frame.id))continue;
      const n=model.node(frame.id);if(!n)continue;
      const ids=childIds(n.id),v={...n,x:frame.depth*DX,y:0,depth:frame.depth,childCount:ids.length,titleCount:titleCount(n)};
      nodes.push(v);byId.set(v.id,v);
      if(frame.parent){
        const edge={source:frame.parent.id,target:v.id,label:edgeLabel(frame.parent,v),...(v.unitId?{relationship:'matched organization and unit level',organization_code:v.org,organization_level_code:v.raw.organization_level_code,association_id:v.associationId,source_datasets:[model.datasets.units,model.datasets.designations]}:{})};
        edges.push(edge);incoming.set(v.id,edge);
      }
      const expanded=[];
      if(n.kind==='unit'&&state.includeDesignations&&state.titlesOpen.has(n.id))expanded.push(...model.unitDesignationIds(n));
      if(state.open.has(n.id))for(const id of ids)expanded.push(id);
      stack.push({finish:true,node:v,ids:expanded});
      for(let i=expanded.length-1;i>=0;i--)stack.push({id:expanded[i],depth:frame.depth+1,parent:v});
    }
    const byY=nodes.slice().sort((a,b)=>a.y-b.y);
    const bounds=nodes.reduce((b,n)=>({xmax:Math.max(b.xmax,n.x+W),ymin:Math.min(b.ymin,n.y),ymax:Math.max(b.ymax,n.y+H)}),{xmax:0,ymin:Infinity,ymax:-Infinity});
    view={nodes,edges,byId,byY,incoming,bounds,drawnNodes:0,drawnEdges:0};
    const real=nodes.filter(n=>['org','unit','designation'].includes(n.kind));
    $('visible-count').textContent=fmt(real.length)+' records expanded';
    $('focus-title').textContent=state.focus?model.node(state.focus)?.name||model.scope.name+' organizations':model.scope.name+' organizations';
    $('up-button').disabled=!state.focus;
    const path=state.focus?model.ancestors(state.focus):[];
    $('breadcrumbs').innerHTML='<button data-focus="">All organizations</button>'+path.map(id=>' <span>›</span> <button data-focus="'+esc(id)+'" title="'+esc(model.node(id).name)+'">'+esc(model.node(id).name)+'</button>').join('');
  }
  function nodesBetween(ymin,ymax){
    const sorted=view.byY||[];let low=0,high=sorted.length;
    while(low<high){const mid=(low+high)>>>1;if(sorted[mid].y<ymin-H)low=mid+1;else high=mid;}
    const found=[];for(let i=low;i<sorted.length&&sorted[i].y<=ymax;i++)found.push(sorted[i]);return found;
  }
  function fit(readable=false) {
    if(!view.nodes.length)return;
    const {xmax,ymin,ymax}=view.bounds;
    zoom=Math.min(1.08,(width-70)/(xmax+10),(height-65)/(ymax-ymin+10));zoom=Math.max(readable?.78:.000005,zoom);
    tx=(width-xmax*zoom)/2;ty=(height-(ymax-ymin)*zoom)/2-ymin*zoom;
    if(readable&&(xmax*zoom>width-50||(ymax-ymin)*zoom>height-40)){
      const selected=view.byId.get(state.selected)||view.nodes[0];
      if(xmax*zoom>width-50)tx=Math.min(35,width*.36-selected.x*zoom);
      if((ymax-ymin)*zoom>height-40)ty=Math.max(height-35-ymax*zoom,Math.min(35-ymin*zoom,height/2-(selected.y+H/2)*zoom));
    }
    requestDraw();
  }
  function color(n){return n.kind==='org'?'#496bb6':n.kind==='unit'?'#237f78':isTitle(n)?'#905a96':'#8794a2';}
  function wrap(text,maxWidth,maxLines=2){const out=[];let line='';for(const word of String(text).split(/\s+/)){const next=line?line+' '+word:word;if(ctx.measureText(next).width>maxWidth&&line){out.push(line);line=word;if(out.length===maxLines-1)break;}else line=next;}if(out.length<maxLines)out.push(line);const used=out.join(' ');if(used.length<String(text).trim().length){let last=out.at(-1);while(last&&ctx.measureText(last+'…').width>maxWidth)last=last.slice(0,-1);out[out.length-1]=last+'…';}return out;}
  function cardControls(n){
    const rect=(kind,column,row,label,fill,enabled=true)=>({kind,x:14+column*125,y:H-56+row*26,w:117,h:20,label,fill,enabled});
    const children=rect('children',1,1,(n.childCount?(state.open.has(n.id)?'− ':'+ '):'')+'Children '+fmt(n.childCount),'#647b91',Boolean(n.childCount));
    if(n.kind!=='unit')return n.childCount?[children]:[];
    const location=hasLocation(n),coverage=model.coverageClaimsFor(n).length;
    return [
      rect('location',0,0,location?(referenceIs(n.id,'location')?'− ':'+ ')+'Location':'Location 0','#947134',location),
      rect('coverage',1,0,(coverage?(referenceIs(n.id,'coverage')?'− ':'+ '):'')+'Coverage '+fmt(coverage),'#b14d38',coverage>0),
      rect('titles',0,1,(n.titleCount?(state.includeDesignations&&state.titlesOpen.has(n.id)?'− ':'+ '):'')+'Titles '+fmt(n.titleCount),'#905a96',Boolean(n.titleCount)),
      children
    ];
  }
  function cardButton(n,button){
    ctx.fillStyle=button.enabled?button.fill:'#edf0f3';ctx.beginPath();ctx.roundRect(n.x+button.x,n.y+button.y,button.w,button.h,4);ctx.fill();
    ctx.fillStyle=button.enabled?'white':'#83909d';ctx.font='600 10px -apple-system, sans-serif';ctx.textAlign='center';ctx.fillText(button.label,n.x+button.x+button.w/2,n.y+button.y+14);ctx.textAlign='left';
  }
  function draw(){
    raf=0;const ratio=window.devicePixelRatio||1;ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,width,height);ctx.translate(tx,ty);ctx.scale(zoom,zoom);
    const visible=nodesBetween(-ty/zoom,(height-ty)/zoom).filter(n=>n.x*zoom+tx+W*zoom>=0&&n.x*zoom+tx<=width);
    view.drawnNodes=0;view.drawnEdges=0;
    // A connection can cross the viewport even when neither endpoint card is
    // visible. Cull the curve's bounds independently, and batch strokes by style.
    const xmin=-tx/zoom,xmax=(width-tx)/zoom,ymin=-ty/zoom,ymax=(height-ty)/zoom;
    const edgeGroups=new Map();
    if(zoom>.18)for(const edge of view.edges){
      const a=view.byId.get(edge.source),b=view.byId.get(edge.target),ax=a.x+W,ay=a.y+H/2,bx=b.x,by=b.y+H/2;
      if(bx<xmin||ax>xmax||Math.max(ay,by)<ymin||Math.min(ay,by)>ymax)continue;
      const dashed=/membership|grouped|no parent|title|designation/.test(edge.label),style=edge.association_id?'title':dashed?'association':'parent';
      if(!edgeGroups.has(style))edgeGroups.set(style,[]);
      edgeGroups.get(style).push({edge,ax,ay,bx,by,dashed});
    }
    for(const [style,connections] of edgeGroups){
      ctx.strokeStyle=style==='title'?'#bc9bc2':style==='association'?'#b7c5d2':'#9cabbc';ctx.lineWidth=1.3;ctx.setLineDash(connections[0].dashed?[4,4]:[]);ctx.beginPath();
      for(const {ax,ay,bx,by} of connections){ctx.moveTo(ax,ay);ctx.bezierCurveTo(ax+42,ay,bx-42,by,bx,by);}
      ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=ctx.strokeStyle;ctx.beginPath();
      for(const {bx,by} of connections)if(bx>=xmin&&bx<=xmax&&by>=ymin&&by<=ymax){ctx.moveTo(bx,by);ctx.lineTo(bx-5,by-3);ctx.lineTo(bx-5,by+3);ctx.closePath();}
      ctx.fill();view.drawnEdges+=connections.length;
      if(state.labels&&zoom>.32)for(const {edge,ax,ay,bx,by} of connections){
        const lx=(ax+bx)/2,midY=(ay+by)/2;if(!edge.label||lx<xmin||lx>xmax||midY<ymin-30||midY>ymax+30)continue;
        ctx.font='10px -apple-system, sans-serif';const lines=wrap(edge.label,DX-W-12,3),ly=midY-(lines.length-1)*6;ctx.textAlign='center';
        lines.forEach((line,i)=>{const tw=ctx.measureText(line).width,y=ly+i*12;ctx.fillStyle='#f8fafc';ctx.fillRect(lx-tw/2-3,y-14,tw+6,13);ctx.fillStyle='#657789';ctx.fillText(line,lx,y-5);});ctx.textAlign='left';
      }
    }
    const pixels=new Set();
    for(const n of visible){
      if(zoom<.25){const pixel=Math.round(n.x*zoom+tx)+':'+Math.round(n.y*zoom+ty)+':'+n.kind;if(pixels.has(pixel))continue;pixels.add(pixel);ctx.fillStyle=color(n);ctx.fillRect(n.x,n.y,W,Math.max(H,1/zoom));view.drawnNodes++;continue;}
      view.drawnNodes++;
      const selected=n.id===state.selected,displayGroup=['group','designation-group','designation-level'].includes(n.kind);
      ctx.fillStyle=displayGroup?(isTitle(n)?'#f7f2f8':'#f2f5f8'):'#ffffff';ctx.strokeStyle=selected?color(n):'#d3dde6';ctx.lineWidth=selected?2.3:1;ctx.setLineDash(n.reference||displayGroup?[5,4]:[]);ctx.beginPath();ctx.roundRect(n.x,n.y,W,H,9);ctx.fill();ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle=color(n);ctx.beginPath();ctx.roundRect(n.x,n.y,4,H,[9,0,0,9]);ctx.fill();
      ctx.fillStyle=color(n);ctx.font='600 9px -apple-system, sans-serif';const tag=n.kind==='group'?'DISPLAY GROUP · NO PARENT UNIT':(n.type||n.kind).toUpperCase()+(n.reference?' · REFERENCE':'');ctx.fillText(tag.slice(0,43),n.x+14,n.y+17);
      ctx.font='500 12px -apple-system, sans-serif';ctx.fillStyle='#253749';wrap(n.name,W-32,2).forEach((line,i)=>ctx.fillText(line,n.x+14,n.y+35+i*16));
      ctx.font='10px ui-monospace, monospace';ctx.fillStyle='#81909e';let foot=n.kind==='group'?fmt(n.count)+' members · level '+(n.code||'blank'):n.kind==='designation-group'?fmt(n.count)+' associations':n.kind==='designation-level'?fmt(n.count)+' titles'+(LGDGraph.valid(n.code)?' · level '+n.code:''):n.kind==='designation'?[n.code,titleLevelLabel(n)].filter(Boolean).join(' · '):n.kind==='org'?n.code+' · depth '+n.organizationDepth:n.code;
      if(n.kind==='unit'&&model.carriedUnits.has(n.code))foot+=' · retained';ctx.fillText(foot.slice(0,43),n.x+14,n.y+70);
      for(const control of cardControls(n))cardButton(n,control);
    }
    $('zoom-label').textContent=(zoom<.01?(zoom*100).toFixed(3):Math.round(zoom*100))+'%';
    renderReference();
  }
  function requestDraw(){if(!raf)raf=requestAnimationFrame(draw);}
  function refresh(shouldFit=true,anchorId=null){const before=view.byId?.get(anchorId);buildView();if(shouldFit)fit(true);else{const after=view.byId.get(anchorId);if(before&&after){tx+=(before.x-after.x)*zoom;ty+=(before.y-after.y)*zoom;}requestDraw();}}
  function resetInspect(){state.tab='meaning';state.coveragePage=0;state.coverageQuery='';state.rolesPage=0;state.childrenScroll=0;}
  function enableKind(n){if(n?.kind==='unit'||n?.kind==='group'||n?.unitId)state.includeUnits=true;if(n&&isTitle(n))state.includeDesignations=true;$('show-units').checked=state.includeUnits;$('show-designations').checked=state.includeDesignations;}
  function focus(id){if(id&&!model.node(id))return;enableKind(model.node(id));state.focus=id||null;state.open.clear();state.titlesOpen.clear();state.reference=null;referenceContext=null;if(id)state.open.add(id);state.selected=id||model.roots[0];resetInspect();refresh();inspect();saveHash();}
  function select(id,reveal=false){const n=node(id);if(!n)return;
    state.selected=id;resetInspect();enableKind(n);
    if(reveal&&['designation-group','designation-level'].includes(n.kind))state.open.add(id);
    if(reveal){const path=model.ancestors(id);if(isTitle(n)&&!n.unitId&&(!model.node(state.focus)||!isTitle(model.node(state.focus))))state.focus='designations:'+n.org;else if(!state.focus||!path.includes(state.focus))state.focus=path.find(p=>model.node(p).kind==='org')||id;openPath(id);}
    refresh(reveal,id);inspect();saveHash();
  }
  function toggleTitles(id){const n=model.node(id);if(n?.kind!=='unit'||!titleCount(n))return;if(state.titlesOpen.has(id)&&state.includeDesignations)state.titlesOpen.delete(id);else{state.titlesOpen.add(id);state.includeDesignations=true;$('show-designations').checked=true;}refresh(false,id);inspect();}
  function showLocation(id){toggleReference(id,'location');}
  function showCoverage(id){toggleReference(id,'coverage');}
  function referenceIs(id,kind){return state.reference?.unitId===id&&state.reference?.kind===kind;}
  function closeReference(){state.reference=null;referenceContext=null;$('reference-panel').hidden=true;requestDraw();}
  function toggleReference(id,kind){
    const unit=model.node(id);
    if(unit?.kind!=='unit'||(kind==='location'&&!hasLocation(unit))||(kind==='coverage'&&!model.coverageClaimsFor(unit).length))return;
    if(referenceIs(id,kind)){closeReference();return;}
    const n=view.byId.get(id);
    if(!n||n.x*zoom+tx+W*zoom<0||n.x*zoom+tx>width||n.y*zoom+ty+H*zoom<0||n.y*zoom+ty>height)select(id,true);
    state.reference={unitId:id,kind,query:'',scroll:0};referenceContext=null;
    $('hover-tip').hidden=true;renderReference();requestDraw();
  }
  function inspectReference(){
    if(!state.reference)return;
    const {unitId,kind,query}=state.reference;
    state.selected=unitId;resetInspect();state.tab=kind==='location'?'location':'coverage';state.coverageQuery=query;
    inspect();saveHash();requestDraw();
  }
  function coverageText(r){return [r.covered_entity_name,r.covered_entity_type,r.covered_entity_code,r.coverage_details_reported==='true'?'':'Coverage details not supplied'].join(' ').toLowerCase();}
  function filterReferenceCoverage(){
    const ref=state.reference,context=referenceContext;if(!ref||ref.kind!=='coverage'||!context)return;
    const query=ref.query.trim().toLowerCase();
    const matcher=LGDGraph.createSearchMatcher(query);
    context.filtered=query?context.rows.filter(r=>matcher.test(coverageText(r))):context.rows;
    $('reference-count').textContent=(query?fmt(context.filtered.length)+' of '+fmt(context.rows.length):fmt(context.rows.length))+' coverage records';
    $('reference-spacer').style.height=(context.filtered.length*76)+'px';
    const empty=$('reference-empty');empty.hidden=Boolean(context.filtered.length);empty.textContent=context.rows.length?'No coverage records match this search.':context.missingDetails?'LGD did not supply coverage details for this unit.':'No coverage records were supplied for this unit.';
    $('reference-list').hidden=!context.filtered.length;
    $('reference-list').scrollTop=ref.scroll;renderReferenceRows();
  }
  function renderReferenceRows(){
    const ref=state.reference,context=referenceContext,list=$('reference-list');if(!ref||ref.kind!=='coverage'||!context||!list)return;
    ref.scroll=list.scrollTop;
    const start=Math.max(0,Math.floor(list.scrollTop/76)-3),end=Math.min(context.filtered.length,start+Math.ceil(list.clientHeight/76)+7);
    $('reference-rows').innerHTML=context.filtered.slice(start,end).map((r,i)=>{
      const supplied=r.coverage_details_reported==='true',flag=r.coverage_type==='F'?'Full':r.coverage_type==='P'?'Partial':'Coverage flag not supplied';
      return '<div class="reference-row" role="listitem" aria-posinset="'+(start+i+1)+'" aria-setsize="'+context.filtered.length+'" style="top:'+((start+i)*76)+'px">'+(supplied?'<strong title="'+esc(r.covered_entity_name||'Name not supplied')+'">'+esc(r.covered_entity_name||'Name not supplied')+'</strong><small>'+esc(r.covered_entity_type||'Type not supplied')+' · code '+esc(r.covered_entity_code||'(blank)')+'</small><span class="coverage-flag '+(r.coverage_type==='P'?'partial':'')+'">'+flag+'</span>':'<strong>Coverage details not supplied</strong><small>This does not mean zero coverage.</small>')+'</div>';
    }).join('');
  }
  function renderReference(){
    const panel=$('reference-panel'),ref=state.reference,n=ref&&view.byId?.get(ref.unitId);
    if(!ref||!n||loadingScope||n.x*zoom+tx+W*zoom<0||n.x*zoom+tx>width||n.y*zoom+ty+H*zoom<0||n.y*zoom+ty>height){panel.hidden=true;return;}
    const key=state.scope+':'+ref.kind+':'+ref.unitId;
    if(referenceContext?.key!==key||referenceContext.model!==model){
      const allCoverage=ref.kind==='coverage'?model.coverageFor(n):[];
      referenceContext={key,model,rows:allCoverage.filter(r=>r.coverage_details_reported==='true'),filtered:[],missingDetails:allCoverage.some(r=>r.coverage_details_reported!=='true')};
      panel.dataset.kind=ref.kind;panel.dataset.unit=ref.unitId;
      panel.setAttribute('aria-label',(ref.kind==='location'?'Location':'Coverage')+' for '+n.name);
      let html='<div class="reference-heading"><strong>'+(ref.kind==='location'?'Location reference':'Coverage')+'</strong><button data-reference-close aria-label="Close '+ref.kind+' box">×</button></div><p class="reference-owner">'+esc(n.name)+' <small>· Unit '+esc(n.code)+'</small></p>';
      if(ref.kind==='location'){
        const l=model.location(n),present=LGDGraph.valid(l.type)&&LGDGraph.valid(l.code);
        const name=l.resolved||(!l.unlabelled?l.reportedNames.join(' / '):'')||(present?'Entity '+l.code:'No location reference supplied');
        html+='<div class="reference-location"><h3>'+esc(name)+'</h3><dl><div><dt>Type</dt><dd>'+esc(l.typeName||'Unlabelled')+' <code>'+esc(l.type||'(blank)')+'</code></dd></div><div><dt>Entity code</dt><dd><code>'+esc(l.code||'(blank)')+'</code></dd></div></dl>'+(l.unlabelled&&present?'<p class="muted">No verified entity name is available for this unlabelled type.</p>':'')+'</div>';
      }else html+='<input id="reference-search" class="mini-search" type="search" placeholder="Place, type or code" aria-label="Search this unit’s coverage" value="'+esc(ref.query)+'"><p id="reference-count" aria-live="polite"></p><div id="reference-list" class="reference-list" role="list" tabindex="0" aria-label="All coverage rows"><div id="reference-spacer"><div id="reference-rows"></div></div></div><p id="reference-empty" class="muted" hidden></p>';
      panel.innerHTML=html+'<div class="reference-actions"><button data-reference-inspect>View source details</button></div>';
      panel.hidden=false;
      if(ref.kind==='coverage'){
        filterReferenceCoverage();
        $('reference-search').addEventListener('input',e=>{state.reference.query=e.target.value;state.reference.scroll=0;filterReferenceCoverage();positionReference(view.byId.get(state.reference.unitId)||n);});
        $('reference-list').addEventListener('scroll',renderReferenceRows,{passive:true});
      }
    }
    panel.hidden=false;positionReference(n);
  }
  function positionReference(n){
    const panel=$('reference-panel');panel.style.width='';
    let pw=panel.offsetWidth,ph=panel.offsetHeight;
    const left=n.x*zoom+tx,top=n.y*zoom+ty,right=left+W*zoom,bottom=top+H*zoom;
    let x=left,y=bottom+10;
    if(y+ph>height-8){
      if(top-ph-10>=8)y=top-ph-10;
      else if(width-right-18>=230){panel.style.width=Math.min(pw,width-right-18)+'px';pw=panel.offsetWidth;ph=panel.offsetHeight;x=right+10;y=top;}
      else if(left-18>=230){panel.style.width=Math.min(pw,left-18)+'px';pw=panel.offsetWidth;ph=panel.offsetHeight;x=left-pw-10;y=top;}
      else y=height-ph-8;
    }
    panel.style.left=Math.max(8,Math.min(width-pw-8,x))+'px';panel.style.top=Math.max(8,Math.min(height-ph-8,y))+'px';
  }
  function toggle(id){if(state.open.has(id))state.open.delete(id);else state.open.add(id);refresh(false,id);inspect();}
  function saveHash(){const hash='#scope='+encodeURIComponent(state.scope)+'&focus='+encodeURIComponent(state.focus||'')+'&selected='+encodeURIComponent(state.selected||'');try{history.replaceState(null,'',hash);}catch{}}
  function fieldRows(record){return '<dl class="fields">'+Object.entries(record).map(([f,v])=>'<div class="field-row"><dt>'+esc(f)+'</dt><dd>'+(v==null?'<span class="muted">NULL</span>':v===''?'<span class="muted">blank</span>':esc(typeof v==='object'?JSON.stringify(v):v))+'</dd></div>').join('')+'</dl>';}
  function jump(id,label){return '<button data-jump="'+esc(id)+'">'+esc(label||model.node(id)?.name||id)+'</button>';}
  function relationship(label,content,fields){return '<div class="relationship"><span class="rel-label">'+esc(label)+'</span>'+content+(fields?'<code>'+esc(fields)+'</code>':'')+'</div>';}
  function sourceDate(dataset){const source=payload.sources[dataset];return source?'<p class="source-date">'+esc(dataset)+' · reported '+nice(source.date)+'</p>':'';}
  function rawSection(dataset,rows,extra=''){if(!rows.length)return '';return '<details class="raw-source" open><summary>'+esc(dataset)+' · '+fmt(rows.length)+' row'+(rows.length===1?'':'s')+'</summary>'+sourceDate(dataset)+(extra?'<p>'+esc(extra)+'</p>':'')+rows.slice(0,8).map(r=>fieldRows(r)).join('')+(rows.length>8?'<p>First 8 rows shown. Download this source from Data sources for all rows.</p>':'')+'</details>';}
  function roles(n){return model.designationRows(n);}
  function claims(n){return n.kind==='unit'?model.coverageFor(n):model.rows('org_unit_coverage').filter(r=>r.organization_code===(n.org||n.code));}
  let inspectorListIds=[];
  function recordList(ids,label){inspectorListIds=ids;return '<div id="child-list" class="children-scroll" tabindex="0" role="list" aria-label="'+esc(label)+'" style="height:'+Math.min(320,ids.length*56)+'px"><div class="children-spacer" style="height:'+(ids.length*56)+'px"><div id="child-items"></div></div></div>';}
  function renderChildList(){
    const list=$('child-list');if(!list)return;
    state.childrenScroll=list.scrollTop;
    const start=Math.max(0,Math.floor(list.scrollTop/56)-4),end=Math.min(inspectorListIds.length,start+Math.ceil(list.clientHeight/56)+9);
    $('child-items').innerHTML=inspectorListIds.slice(start,end).map((id,i)=>{const n=model.node(id),count=childIds(id).length;return '<div role="listitem" aria-posinset="'+(start+i+1)+'" aria-setsize="'+inspectorListIds.length+'" class="virtual-child" style="top:'+((start+i)*56)+'px"><button class="child-link" data-jump="'+esc(id)+'"><i class="dot '+(isTitle(n)?'designation':n.kind==='unit'?'unit':'')+'"></i><span class="child-text"><span>'+esc(n.name)+'</span><small>'+esc([n.code||'Display group',n.kind==='designation'?titleLevelLabel(n):''].filter(Boolean).join(' · '))+'</small></span>'+(count?'<span class="count">'+fmt(count)+' ›</span>':'')+'</button></div>';}).join('');
  }
  function childrenSection(n){const ids=childIds(n.id),label=isTitle(n)?'Reported levels / titles':n.kind==='unit'?'Child units':n.kind==='group'?'Member units':'Child organizations / member units';return '<div class="section"><h3>'+label+' · '+fmt(ids.length)+'</h3>'+(ids.length?recordList(ids,'All '+ids.length+' '+label.toLowerCase()):'<p class="muted">No children with the current filters.</p>')+'</div>';}
  function locationSection(n){
    const l=model.location(n);let html='<div id="location-section" class="section"><h3>Location reference</h3><p class="source-date">The unit supplies one entity type/code pair. Coverage is a separate list of places under Coverage.</p>'+relationship(l.typeName||'Unlabelled entity type '+(l.type||'(blank)'),'<p><strong>'+esc(l.resolved||(!l.unlabelled?l.reportedNames.join(' / '):'')||'No verified entity name available')+'</strong></p>','entity_type = '+JSON.stringify(l.type)+'; entity_code = '+JSON.stringify(l.code));
    if(l.admin)html+='<p class="source-date">Name lookup: '+esc(model.datasets.adminEntities)+', matched on both administrative_unit_level_code and administrative_unit_code. Type name: '+esc(model.datasets.adminLevels)+' or the matching details row.</p>';
    else if(model.geo.has(LGDGraph.key(l.type,l.code)))html+='<p class="source-date">Entity name independently resolved in the '+(l.type==='1'?'state':'district')+' register. The type label is also supplied in the details report.</p>';
    else if(l.details.length)html+='<p class="source-date">Name claims come from details rows matching the same unit, organization, entity type and entity code.</p>';
    if(l.reportedNames.length)html+='<p class="source-date">Details report’s entity_name: '+esc(l.reportedNames.join(' / '))+'</p>';
    if(l.type==='-100')html+='<div class="notice">The source leaves this type’s name blank. These international embassy references can have incorrect district names in entity_name; their supplied names are not treated as verified.</div>';
    if(!LGDGraph.valid(l.type)||!LGDGraph.valid(l.code))html+='<p class="source-date">The reference is blank or uses a zero code. It is not treated as a named geographic entity.</p>';
    const different=model.detailsFor(n).filter(d=>d.entity_type!==l.type||d.entity_code!==l.code);
    if(different.length)html+='<div class="notice">The details report contains a different reference. Source rows preserve both claims; it has not replaced the directory location.</div>';
    return html+sourceDate(n.source)+'</div>';
  }
  function inspectorActions(n){
    const focusButton='<button data-focus="'+esc(n.id)+'">Focus this branch</button>';
    if(n.kind!=='unit')return focusButton+(childIds(n.id).length?'<button data-toggle="'+esc(n.id)+'">'+(state.open.has(n.id)?'Collapse':'Expand all')+' children</button>':'');
    const attributes={location:'data-location',coverage:'data-coverage',titles:'data-titles',children:'data-toggle'};
    return focusButton+cardControls({...n,childCount:childIds(n.id).length,titleCount:titleCount(n)}).map(control=>'<button '+attributes[control.kind]+'="'+esc(n.id)+'"'+(control.enabled?'':' disabled')+'>'+esc(['location','coverage'].includes(control.kind)?control.label.replace(/^[+−] /,''):control.label)+'</button>').join('');
  }
  function inspect(scrollId){inspectorListIds=[];const n=model.node(state.selected);if(!n){$('inspector').innerHTML='<div class="empty-inspector">No organization records are available for '+esc(model.scope.name)+'.</div>';return;}
    const subtitle=n.kind==='org'?'An organization. Its child organizations and member offices are separate kinds of relationship.':n.kind==='unit'?'An office or unit. Its organization, parent office, own level and location reference are separate fields.':n.kind==='designation'?'A designation title associated with this organization and reported level. It does not identify a person or confirm staffing at an office.':isTitle(n)?'A display group of designation records, organized by the level supplied in the designation report.':'A display group of member units with no reported parent unit. This is not an LGD entity or an inferred parent.';
    const tabs=isTitle(n)?[['meaning','Relationships'],['raw','Source rows']]:[['meaning','Relationships'],...(n.kind==='unit'?[['location','Location']]:[]),['raw','Source rows'],['coverage','Coverage'],['roles','Titles']];
    if(!tabs.some(([id])=>state.tab===id))state.tab='meaning';
    const idLabel=n.kind==='org'?'Organization code':n.kind==='unit'?'Unit code':n.kind==='designation'?'Designation code':n.kind==='designation-level'&&LGDGraph.valid(n.code)?'Reported level code':null;
    let html='<div class="inspector-header"><span class="badge '+(isTitle(n)?'designation':n.kind==='unit'?'unit':n.kind==='group'?'group':'')+'">'+esc(n.type||n.kind)+'</span>'+(n.reference?'<span class="badge warn">Reference only</span>':'')+'<h2>'+esc(n.name)+'</h2><div class="id-line">'+(idLabel?esc(idLabel)+' <code>'+esc(n.code||'(blank)')+'</code>':'Display group')+'</div><p>'+subtitle+'</p><div class="inspector-actions '+(n.kind==='unit'?'unit-actions':'')+'">'+inspectorActions(n)+'</div></div><div class="tabs">'+tabs.map(([id,label])=>'<button data-tab="'+id+'" class="'+(state.tab===id?'active':'')+'">'+label+'</button>').join('')+'</div><div class="inspector-body">';
    if(state.tab==='meaning'){
      if(n.reference)html+='<div class="notice">This identifier is referenced by another report, but has no independent row in the main organization or unit directory. The graph preserves the reference.</div>';
      if(n.kind==='org'){
        const childOrgs=childIds(n.id).filter(id=>model.node(id).kind==='org'),units=model.orgUnits.get(n.code)||[];
        html+='<div class="metric-row"><div class="metric"><strong>'+fmt(childOrgs.length)+'</strong><span>Child organizations</span></div><div class="metric"><strong>'+fmt(units.length)+'</strong><span>Member units</span></div></div>';
        html+=relationship('Reported parent organization',LGDGraph.valid(n.raw.parent_organization_code)?jump('org:'+n.raw.parent_organization_code,n.raw.parent_organization_name):'<p>No parent organization supplied.</p>','parent_organization_code = '+JSON.stringify(n.raw.parent_organization_code??''));
        html+='<p class="source-date">Organization depth '+n.organizationDepth+': '+n.organizationDepth+' reported parent link'+(n.organizationDepth===1?'':'s')+' from the top of the available chain. A reference without its own parent row ends the chain.</p>';
        if(model.designations.has(n.code))html+=relationship('Designation source catalogue',jump('designations:'+n.code,fmt(model.designations.get(n.code).length)+' title records')+'<p class="source-date">Browse the titles and level names reported for this organization.</p>',model.datasets.designations+'.organization_code = '+n.code);
        html+='<p class="source-date">Unit membership comes from each unit’s organization_code. A member unit need not be a child of the organization’s head office.</p>'+sourceDate(model.datasets.orgs);
      } else if(n.kind==='unit'){
        html+=relationship('Belongs to organization',jump('org:'+n.org),'organization_code = '+n.org);
        html+=relationship('Reported parent office / unit',LGDGraph.valid(n.raw.parent_organization_unit_code)?jump('unit:'+n.raw.parent_organization_unit_code,n.raw.parent_organization_unit_name):'<p>No parent unit supplied. Membership alone does not identify its parent office.</p>','parent_organization_unit_code = '+JSON.stringify(n.raw.parent_organization_unit_code??''));
        const names=[...new Set(model.levelNames.get(LGDGraph.key(n.org,n.raw.organization_level_code))||[])];
        html+=relationship('Office’s own organizational level','<p>'+esc(names.join(' / ')||'No level name available in the designation report.')+'</p>','organization_level_code = '+JSON.stringify(n.raw.organization_level_code??''));
        const titles=model.unitDesignationIds(n);
        const orgTitles=model.designations.get(n.org)||[];
        html+=relationship('Designations for this unit’s level',titles.length?titles.slice(0,8).map(id=>jump(id)).join('')+(titles.length>8?'<p>'+fmt(titles.length)+' matches. Expand this unit or open Titles to browse all of them.</p>':''):'<p>No matching designation rows in the current report.</p>'+(orgTitles.length?jump('designations:'+n.org,'Browse the organization’s '+fmt(orgTitles.length)+' title records'):''),'Matched on organization_code + organization_level_code');
        const l=model.location(n);html+=relationship('Location reference',hasLocation(n)?'<button data-location="'+esc(n.id)+'">'+esc([l.typeName,l.resolved||(!l.unlabelled?l.reportedNames.join(' / '):'')].filter(Boolean).join(' · ')||'View supplied location fields')+'</button>':'<p>No location reference supplied.</p>','entity_type + entity_code');
        if(model.carriedUnits.has(n.code))html+='<div class="notice">Retained in the latest export; this unit was last actually supplied on '+nice(model.carriedUnits.get(n.code))+'. It was not reconfirmed by the latest report.</div>';
        html+=sourceDate(n.source);
      } else if(isTitle(n)){
        if(n.unitId)html+=relationship('Associated unit through its level',jump(n.unitId),'Unit '+model.node(n.unitId).code+' and this designation both have organization_code = '+n.org+' and organization_level_code = '+n.raw.organization_level_code);
        html+=relationship('Reported organization',jump('org:'+n.org),'organization_code = '+n.org);
        if(n.kind==='designation'||n.kind==='designation-level'){
          html+=relationship('Reported organizational level',n.kind==='designation'?jump(LGDGraph.designationLevelId(n.raw),titleLevelLabel(n)||'Level not supplied'):'<p>'+esc(titleLevelLabel(n)||'Level not supplied')+'</p>',(LGDGraph.valid(n.raw.organization_level_code)?'organization_level_code = '+JSON.stringify(n.raw.organization_level_code)+'; ':'')+'organization_level_name = '+JSON.stringify(n.raw.organization_level_name??''));
        }
        if(n.kind!=='designation')html+='<p>'+fmt(n.count)+' designation association'+(n.count===1?'':'s')+'. These display groups are not offices or additional organization records.</p>';
        else if(!n.unitId){const matches=model.unitsForDesignation(n);if(matches.length)html+=relationship('Units with this organization and level',matches.slice(0,8).map(id=>jump(LGDGraph.unitDesignationId(id,n.id),model.node(id).name)).join('')+(matches.length>8?'<p>'+fmt(matches.length)+' matching units; first 8 shown.</p>':''),'organization_code + organization_level_code');}
        html+=sourceDate(model.datasets.designations);
      } else html+='<div class="notice">'+fmt(n.count)+' units share an organizational level and lack a reported parent unit. This grouping adds no source relationship.</div>';
      if(n.kind!=='designation')html+=childrenSection(n);
    } else if(state.tab==='location'){html+=locationSection(n);
    } else if(state.tab==='raw'){
      if(n.kind==='org'){
        if(!n.reference)html+=rawSection(model.datasets.orgs,[n.raw]);
        else html+='<p class="muted">No independent organization row. The label was supplied by referring organization, unit or designation records.</p>';
      } else if(n.kind==='unit'){
        html+=rawSection(n.source||model.datasets.units,[n.raw]);
        const all=model.detailsFor(n),same=all.filter(d=>d.entity_type===n.raw.entity_type&&d.entity_code===n.raw.entity_code);
        html+=rawSection('org_unit_details',all,all.length!==same.length?'The source contains a different location claim. It has not replaced the directory’s typed location.':'Joined on unit and organization; location enrichment additionally matches entity_type and entity_code.');
        const l=model.location(n);if(l.level)html+=rawSection(model.datasets.adminLevels,[l.level]);if(l.admin)html+=rawSection(model.datasets.adminEntities,[l.admin]);
        if(!all.length)html+='<p class="muted">No corresponding unit-details row was supplied.</p>';
      }else if(isTitle(n)){html+=rawSection(model.datasets.designations,roles(n),n.kind==='designation'?'One reported title–organization–level association. The same designation code can occur in other associations.':'Source rows behind this display group; every supplied level code and name is preserved.');if(n.unitId)html+=rawSection(model.datasets.units,[model.node(n.unitId).raw],'The unit row matches this designation on organization_code and its own organization_level_code.');}
      else html+=fieldRows(n.raw)+'<p class="source-date">This is a display group, not a source row.</p>';
    } else if(state.tab==='coverage'){
      const all=claims(n),supplied=all.filter(r=>r.coverage_details_reported==='true'),missing=all.length-supplied.length;
      const matcher=LGDGraph.createSearchMatcher(state.coverageQuery),filtered=state.coverageQuery.trim()?all.filter(r=>matcher.test([r.covered_entity_name,r.covered_entity_code,r.covered_entity_type,r.organization_unit_name].join(' '))):all;
      html+='<h3>Coverage is separate from location</h3><p class="source-date">Every reported claim is retained, including repeats and missing labels. Full / partial describes the claim. A no-details row does not mean zero coverage. Report selection levels are not the office’s own level.</p><div class="metric-row"><div class="metric"><strong>'+fmt(supplied.length)+'</strong><span>Claim rows</span></div><div class="metric"><strong>'+fmt(missing)+'</strong><span>No-details rows</span></div></div><input class="mini-search" id="coverage-search" placeholder="Filter place, type or code" aria-label="Filter coverage claims" value="'+esc(state.coverageQuery)+'">';
      if(!all.length)html+='<p class="muted">No coverage rows are supplied for this selection.</p>';
      for(const r of filtered.slice(0,(state.coveragePage+1)*40))html+='<div class="claim">'+(r.coverage_details_reported==='true'?'<span class="badge '+(r.coverage_type==='P'?'warn':'')+'">'+(r.coverage_type==='F'?'Full':'Partial')+'</span><b>'+esc(r.covered_entity_name||'(name blank)')+'</b><small>'+esc(r.covered_entity_type||'(type blank)')+' · code '+esc(r.covered_entity_code)+'</small>':'<b>Coverage details not supplied</b>')+'<small>Unit '+esc(r.organization_unit_code)+' · report selection '+esc(r.report_organization_level_name||r.report_organization_level_code)+'</small></div>';
      if(filtered.length>(state.coveragePage+1)*40)html+='<button class="more-button" data-more-coverage>Show 40 more · '+fmt(filtered.length)+' rows</button>';
      html+=sourceDate('org_unit_coverage');
    } else {
      const rows=roles(n);html+='<h3>Designation titles</h3><p class="source-date">These are reported titles, not named people or confirmed staff assignments. '+(n.kind==='unit'?'Only exact nonblank matches to the office’s organization_level_code are shown.':'Each row retains its reported level; blank codes remain blank.')+'</p>';
      if(!rows.length)html+='<p class="muted">No matching designation rows.</p>';
      if(rows.length)html+=recordList(rows.map(r=>n.kind==='unit'?LGDGraph.unitDesignationId(n.id,LGDGraph.designationId(r)):LGDGraph.designationId(r)),'All designation associations');
      html+=sourceDate(model.datasets.designations);
    }
    $('inspector').innerHTML=html+'</div>';
    const list=$('child-list');if(list){list.scrollTop=state.childrenScroll;renderChildList();list.addEventListener('scroll',renderChildList,{passive:true});}
    if(scrollId)$('location-section')?.scrollIntoView({block:'nearest',behavior:'smooth'});
  }
  function renderOrganizations(){let depth=-1;$('organizations').innerHTML=model.organizations.map(n=>{const heading=n.organizationDepth!==depth?'<div class="depth-heading">Depth '+n.organizationDepth+(n.organizationDepth===0?' · Top of available chains':'')+'</div>':'';depth=n.organizationDepth;return heading+'<button class="org-item" data-depth="'+n.organizationDepth+'" data-focus="'+esc(n.id)+'"><i class="dot"></i><span><span class="name">'+esc(n.name)+'</span><small>'+esc(n.type)+' · '+esc(n.code)+' · depth '+n.organizationDepth+'</small></span><span class="count" title="Member units">'+fmt((model.orgUnits.get(n.code)||[]).length)+'</span></button>';}).join('');}
  function search(){const query=$('search').value.trim();$('search-results').hidden=!query;$('browse-panel').hidden=Boolean(query);if(!query)return;const matches=model.search(query,state.searchKind);$('search-results').innerHTML='<p class="result-count">'+fmt(matches.length)+' matches'+(matches.length>60?' · first 60 shown':'')+'</p>'+matches.slice(0,60).map(n=>'<button class="result-item" data-jump="'+esc(n.id)+'"><i class="dot '+(isTitle(n)?'designation':n.kind==='unit'?'unit':'')+'"></i><span><span class="name">'+esc(n.name)+'</span><small>'+esc(n.kind==='unit'?'Unit':n.type)+' · '+esc(n.code)+(n.org?' · organization '+esc(n.org):' · depth '+n.organizationDepth)+(n.kind==='designation'&&titleLevelLabel(n)?' · '+esc(titleLevelLabel(n)):'')+'</small></span></button>').join('');}
  function download(content,name,type='application/json'){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function csv(dataset){const t=payload.tables[dataset],quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';download([t.fields,...t.rows].map(row=>row.map(quote).join(',')).join('\r\n'),dataset+'.csv','text/csv;charset=utf-8');}
  function sources(){const rows=Object.entries(payload.sources).map(([d,s])=>'<tr><td><code>'+esc(d)+'</code><br><small>'+esc(sourceUse[d])+'</small></td><td>'+nice(s.date)+'</td><td>'+fmt(s.rows)+'</td><td><button data-csv="'+d+'">CSV</button></td></tr>').join('');$('sources-content').innerHTML='<table class="source-table"><thead><tr><th>Dataset and use</th><th>Collected</th><th>Included rows</th><th>Export</th></tr></thead><tbody>'+rows+'</tbody></table><div class="notice">Dashed organization cards are referenced identifiers without a standalone organization row. Grey unit groups are display aids for units with no reported parent. Neither is presented as an invented directory record.</div><p class="muted">Only latest current tables are included. The latest observation metadata identifies retained units that were not freshly supplied. No historical version series is included.</p>';$('sources-dialog').showModal();}
  function zoomAt(factor,x=width/2,y=height/2){const z=Math.min(2.5,Math.max(.000005,zoom*factor));tx=x-(x-tx)*z/zoom;ty=y-(y-ty)*z/zoom;zoom=z;requestDraw();}
  function hit(x,y){const wx=(x-tx)/zoom,wy=(y-ty)/zoom;return nodesBetween(wy,wy).find(n=>wx>=n.x&&wx<=n.x+W&&wy>=n.y&&wy<=n.y+H);}
  let drag=null;
  canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);drag={x:e.offsetX,y:e.offsetY,tx,ty,moved:false};$('hover-tip').hidden=true;});
  canvas.addEventListener('pointermove',e=>{if(drag){const dx=e.offsetX-drag.x,dy=e.offsetY-drag.y;if(Math.hypot(dx,dy)>4)drag.moved=true;if(drag.moved){tx=drag.tx+dx;ty=drag.ty+dy;canvas.style.cursor='grabbing';requestDraw();}return;}const n=hit(e.offsetX,e.offsetY);const control=n&&cardControls(n).find(b=>{const x=(e.offsetX-tx)/zoom-n.x,y=(e.offsetY-ty)/zoom-n.y;return x>=b.x&&x<=b.x+b.w&&y>=b.y&&y<=b.y+b.h;});canvas.style.cursor=control&&!control.enabled?'default':n?'pointer':'grab';if(n){$('hover-tip').textContent=control&&!control.enabled?(control.kind==='location'?'No location reference supplied.':control.kind==='coverage'?'No coverage details supplied.':control.kind==='titles'?'No matching designation titles.':'No child records.') :n.name+(n.code?' · '+n.code:'');$('hover-tip').style.left=Math.min(e.offsetX+12,width-280)+'px';$('hover-tip').style.top=Math.max(5,e.offsetY-50)+'px';$('hover-tip').hidden=false;}else $('hover-tip').hidden=true;});
  canvas.addEventListener('pointerup',e=>{
    if(!drag)return;const moved=drag.moved;drag=null;canvas.style.cursor='grab';if(moved)return;
    const n=hit(e.offsetX,e.offsetY);if(!n)return;
    const x=(e.offsetX-tx)/zoom-n.x,y=(e.offsetY-ty)/zoom-n.y;
    const control=cardControls(n).find(b=>x>=b.x&&x<=b.x+b.w&&y>=b.y&&y<=b.y+b.h);
    if(!control){select(n.id);return;}if(!control.enabled)return;
    if(control.kind==='location')showLocation(n.id);else if(control.kind==='coverage')showCoverage(n.id);else if(control.kind==='titles')toggleTitles(n.id);else toggle(n.id);
  });
  canvas.addEventListener('pointercancel',()=>{drag=null;});canvas.addEventListener('pointerleave',()=>{$('hover-tip').hidden=true;});
  canvas.addEventListener('dblclick',e=>{const n=hit(e.offsetX,e.offsetY);if(n&&model.node(n.id))focus(n.id);});
  canvas.addEventListener('wheel',e=>{e.preventDefault();zoomAt(Math.exp(-e.deltaY*.0015),e.offsetX,e.offsetY);},{passive:false});
  document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.hasAttribute('data-reference-close')){closeReference();return;}if(b.hasAttribute('data-reference-inspect')){inspectReference();return;}if(b.hasAttribute('data-focus'))focus(b.dataset.focus);else if(b.dataset.jump)select(b.dataset.jump,true);else if(b.dataset.toggle)toggle(b.dataset.toggle);else if(b.dataset.tab){state.tab=b.dataset.tab;state.childrenScroll=0;inspect();}else if(b.dataset.titles)toggleTitles(b.dataset.titles);else if(b.dataset.location)showLocation(b.dataset.location);else if(b.dataset.coverage)showCoverage(b.dataset.coverage);else if(b.hasAttribute('data-more-coverage')){state.coveragePage++;inspect();}else if(b.hasAttribute('data-more-roles')){state.rolesPage++;inspect();}else if(b.dataset.csv)csv(b.dataset.csv);else if(b.dataset.kind){state.searchKind=b.dataset.kind;document.querySelectorAll('#search-kinds button').forEach(x=>x.classList.toggle('active',x===b));search();}});
  let timer,coverageTimer;
  $('search').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(search,120);});
  document.addEventListener('input',e=>{if(e.target.id==='coverage-search'){state.coverageQuery=e.target.value;state.coveragePage=0;clearTimeout(coverageTimer);coverageTimer=setTimeout(()=>{const pos=e.target.selectionStart;inspect();const input=$('coverage-search');input.focus();input.setSelectionRange(pos,pos);},180);}});
  $('show-units').addEventListener('change',e=>{state.includeUnits=e.target.checked;refresh(false,state.focus);inspect();});
  $('show-designations').addEventListener('change',e=>{state.includeDesignations=e.target.checked;refresh(false,model.node(state.selected)?.unitId||state.selected);inspect();});
  $('show-labels').addEventListener('change',e=>{state.labels=e.target.checked;requestDraw();});
  $('fit-button').onclick=()=>fit(false);$('zoom-in').onclick=()=>zoomAt(1.25);$('zoom-out').onclick=()=>zoomAt(.8);
  $('collapse-button').onclick=()=>{state.open.clear();state.titlesOpen.clear();refresh(false,state.focus||state.selected);inspect();};
  $('expand-button').onclick=()=>{for(const n of view.nodes)if(model.node(n.id))state.open.add(n.id);refresh(false,state.selected);inspect();};
  $('overview-button').onclick=()=>focus(null);$('up-button').onclick=()=>focus(model.parentId(state.focus)||null);
  $('sources-button').onclick=sources;$('close-sources').onclick=()=>$('sources-dialog').close();
  $('download-data').onclick=()=>download(bytes,'lgd-scope-'+state.scope+'-current-data.json.gz','application/gzip');
  $('download-view').onclick=()=>download(JSON.stringify({scope:model.scope,sources:payload.sources,openReference:state.reference,nodes:view.nodes.map(({x,y,depth,...n})=>n),edges:view.edges,notes:'Display groups are not LGD entities. Location and coverage are separate unit reference boxes, not hierarchy nodes; source details are available in the inspector. Title edges are independently expanded associations, not child offices. Designations associate titles with an organization and reported level, not people or office staffing.'},null,2),'lgd-scope-'+state.scope+'-visible-graph.json');
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&state.reference&&!$('sources-dialog').open){closeReference();e.preventDefault();return;}if(loadingScope||!model||e.target.closest('#child-list, #reference-panel')||['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName))return;if(e.key==='/'){e.preventDefault();$('search').focus();}else if(e.key==='ArrowRight'){e.preventDefault();state.open.add(state.selected);refresh(false,state.selected);inspect();}else if(e.key==='ArrowLeft'){e.preventDefault();if(state.open.has(state.selected)){state.open.delete(state.selected);refresh(false,state.selected);inspect();}else{const p=model.parentId(state.selected);if(p)select(p,true);}}else if(e.key==='Enter'&&e.target===canvas)focus(state.selected);});
  new ResizeObserver(()=>{const box=$('canvas-wrap').getBoundingClientRect();width=box.width;height=box.height;const ratio=window.devicePixelRatio||1;canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);requestDraw();}).observe($('canvas-wrap'));
  $('scope-select').addEventListener('change',e=>changeScope(e.target.value));
  const hash=new URLSearchParams(location.hash.slice(1));
  // Small public inspection surface for reproducible browser checks.
  globalThis.lgdExplorer={get model(){return model;},state,get view(){return view;},get camera(){return {zoom,tx,ty};},focus,select,expand:toggle,expandTitles:toggleTitles,showLocation,showCoverage,fit,inspect,changeScope,get ready(){return Boolean(model)&&!loadingScope;},
    screenPoint(id,control=false){const n=view.byId.get(id);if(!n)return null;const box=canvas.getBoundingClientRect(),button=control&&cardControls(n).find(b=>b.kind===(control===true?'children':control));const x=button?button.x+button.w/2:W/2,y=button?button.y+button.h/2:H/2;return{x:box.left+tx+(n.x+x)*zoom,y:box.top+ty+(n.y+y)*zoom};}};
  await changeScope(scopeMap.has(hash.get('scope'))?hash.get('scope'):'0',hash);
})();
