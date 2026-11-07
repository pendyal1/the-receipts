'use strict';

// Interface copy is bundled; no source or user text is interpreted as markup.
const infoPanels={
 about:`<span class="section-index">01 — ABOUT THE APP</span><h2 id="info-title" class="info-title">The past has<br>a paper trail.</h2><p class="info-lead">For investors and traders who want to compare what a company said with what happened next.</p><div class="info-steps"><div class="info-step"><span>THEN</span><div><h3>What management expected.</h3><p>Return to the filings available at a historical date.</p></div></div><div class="info-step"><span>NEXT</span><div><h3>What the numbers revealed.</h3><p>Compare later financial results and industry peers.</p></div></div><div class="info-step"><span>PROOF</span><div><h3>Evidence you can open.</h3><p>Follow each citation back to the source record.</p></div></div></div><p class="info-small">Historical research, not trading recommendations. Built for Columbia · IEOR 4570.</p>`,
 how:`<span class="section-index">02 — A SHORT FIELD GUIDE</span><h2 id="info-title" class="info-title">Follow the evidence.</h2><div class="info-steps"><div class="info-step"><span>01</span><div><h3>Choose your company.</h3><p>Search a company name or U.S. stock ticker. You can also ask a question that names the company.</p></div></div><div class="info-step"><span>02</span><div><h3>Set the viewpoint.</h3><p>Add up to two peers and choose the history start, what was known by, and how far to follow later results. The default window is 2020–March 2025.</p></div></div><div class="info-step"><span>03</span><div><h3>Cross-examine the record.</h3><p>Read the finding, explore the chart, and open a numbered citation to inspect its evidence. Missing metrics and untestable claims are identified.</p></div></div></div><p class="info-small">Investigations usually take 1–3 minutes. “Browse source data only” opens the records without an AI report.</p>`,
 sources:`<span class="section-index">03 — THE PAPER TRAIL</span><h2 id="info-title" class="info-title">Public records.<br>Open questions.</h2><p class="info-lead">Three perspectives on the same company history.</p><div class="info-steps"><a class="source-row" href="https://www.sec.gov/edgar/search/" target="_blank" rel="noopener noreferrer"><div><strong>SEC EDGAR</strong><p>Management outlook in filings and reported annual financial metrics from XBRL.</p></div><span aria-hidden="true">↗</span></a><a class="source-row" href="https://fred.stlouisfed.org/" target="_blank" rel="noopener noreferrer"><div><strong>FRED</strong><p>Interest rates and inflation for hindsight context. Revised series are not as-of observations.</p></div><span aria-hidden="true">↗</span></a><a class="source-row" href="https://finance.yahoo.com/" target="_blank" rel="noopener noreferrer"><div><strong>Historical prices</strong><p>Vendor-adjusted closing prices via an unofficial Yahoo endpoint. Context, not proof of causation.</p></div><span aria-hidden="true">↗</span></a></div><p class="info-small">Archived examples cover 2020–March 2025. Other companies and dates depend on live availability. Outlook excerpts are a bounded filing search; supported annual metrics cannot test every operational or segment-level claim.</p>`
};
function openResearch(){
 if(state.busy)return;
 if($('info-dialog').open)$('info-dialog').close();
 $('form-notice').hidden=true;
 if(!$('research-dialog').open)$('research-dialog').showModal();
 if(!$('tickers').value)$('tickers').focus();else $('question').focus();
}
function openInfo(panel){
 if(!Object.hasOwn(infoPanels,panel))return;
 if($('research-dialog').open)$('research-dialog').close();
 $('info-content').innerHTML=infoPanels[panel];
 $('info-dialog').querySelectorAll('[data-panel]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.panel===panel)));
 if(!$('info-dialog').open)$('info-dialog').showModal();
}
document.querySelectorAll('[data-panel]').forEach(button=>button.addEventListener('click',()=>openInfo(button.dataset.panel)));
document.querySelectorAll('[data-close-dialog]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
for(const dialog of document.querySelectorAll('dialog'))dialog.addEventListener('click',event=>{const r=dialog.getBoundingClientRect();if(event.target===dialog&&(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom))dialog.close();});
$('info-start').addEventListener('click',()=>{if(state.busy){$('info-dialog').close();return;}openResearch();});

const searchAliases={...names,AAPL:'Apple',META:'Meta',NFLX:'Netflix',AVGO:'Broadcom',PLTR:'Palantir',JPM:'JPMorgan','BRK-B':'Berkshire Hathaway',CRM:'Salesforce',ORCL:'Oracle',GOOG:'Google'};
function searchCompanies(text){
 const matches=[];
 for(const [symbol,name]of Object.entries(searchAliases)){
  const escaped=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const nameMatch=new RegExp('\\b'+escaped+'\\b','i').exec(text);
  const symbolMatch=new RegExp('\\b'+symbol.replace(/[.-]/g,'\\$&')+'\\b',symbol.length===1?'':'i').exec(text);
  if(nameMatch||symbolMatch)matches.push({symbol,index:Math.min(nameMatch?.index??Infinity,symbolMatch?.index??Infinity)});
 }
 matches.sort((a,b)=>a.index-b.index);
 const symbols=[...new Set(matches.map(m=>m.symbol==='GOOG'?'GOOGL':m.symbol))];
 if(!symbols.length&&/^[a-z][a-z0-9.-]{0,9}$/i.test(text))symbols.push(text.toUpperCase());
 if(!symbols.length){const omitted=new Set(['AI','SEC','CEO','USD','CAPEX','THE','AND','FRED','GDP','US']);for(const m of text.matchAll(/\b[A-Z][A-Z0-9.-]{1,9}\b/g)){if(!omitted.has(m[0]))symbols.push(m[0]);}}
 return [...new Set(symbols)];
}
$('search-form').addEventListener('submit',event=>{
 event.preventDefault();if(state.busy)return;
 const text=$('company-search').value.trim();
 if(!text){$('company-search').setCustomValidity('Enter a company name, ticker, or research question.');$('company-search').reportValidity();return;}
 const symbols=searchCompanies(text),primary=symbols[0],name=searchAliases[primary]||primary;
 $('tickers').value=primary?(names[primary]||primary):'';
 $('peers').value=symbols.slice(1).join(', ');
 const justCompany=primary&&(text.toUpperCase()===primary||Object.entries(searchAliases).some(([symbol,label])=>(symbol==='GOOG'?'GOOGL':symbol)===primary&&(text.toLowerCase()===label.toLowerCase()||text.toUpperCase()===symbol)));
 const question=justCompany?`Did ${name} deliver on its plans after 2022?`:text;
 $('question').value=primary?question:text;
 state.autoQuestion=justCompany?question:null;
 $('research-settings').open=symbols.length>1;
 updateScopeCaption();openResearch();
 if(!primary||symbols.length>3){$('form-notice').textContent=!primary?'Add the company’s U.S. stock ticker to continue.':'Choose up to three companies for this investigation.';$('form-notice').hidden=false;}
});
$('company-search').addEventListener('input',()=>$('company-search').setCustomValidity(''));

// A lightweight procedural wireframe: visual atmosphere, never financial data.
const terrain=$('terrain'),terrainContext=terrain.getContext('2d'),motionQuery=matchMedia('(prefers-reduced-motion: reduce)');
let motionEnabled=!motionQuery.matches&&sessionStorage.getItem('receipts-motion')!=='off',terrainWidth=0,terrainHeight=0,terrainFrame=0,lastFrame=0,terrainTime=0,pointerX=0,pointerY=0,targetPointerX=0,targetPointerY=0;
function resizeTerrain(){const r=terrain.getBoundingClientRect(),scale=Math.min(devicePixelRatio||1,1.5);terrainWidth=r.width;terrainHeight=r.height;terrain.width=Math.round(r.width*scale);terrain.height=Math.round(r.height*scale);terrainContext?.setTransform(scale,0,0,scale,0,0);drawTerrain();}
function drawTerrain(){
 if(!terrainContext||!terrainWidth||!terrainHeight)return;
 const ctx=terrainContext,w=terrainWidth,h=terrainHeight,columns=w<700?44:65,rows=w<700?30:43;
 ctx.clearRect(0,0,w,h);ctx.lineWidth=.65;
 const points=[];
 pointerX+=(targetPointerX-pointerX)*.045;pointerY+=(targetPointerY-pointerY)*.045;
 for(let j=0;j<=rows;j++){
  const row=[],z=(j/rows-.5)*9;
  for(let i=0;i<=columns;i++){
   const x=(i/columns-.5)*15;
   const wave=Math.sin(x*.55+terrainTime*.14)*.95+Math.cos(z*.6+terrainTime*.1)*.72+Math.sin(x*.18-z*.5+terrainTime*.07)*.5;
   const depth=1+z*.055;
   row.push([(w*.5+(x+z*.48+pointerX*.18)*w*.085)/depth+(w*.5-w*.5/depth),h*.69+(z*.36-wave*.84-x*.085+pointerY*.1)*h*.16/depth]);
  }points.push(row);
 }
 for(let j=0;j<=rows;j++){
  const isAccent=j===Math.round(rows*.59);
  ctx.strokeStyle=isAccent?'rgba(164,211,117,.29)':'rgba(125,139,115,.22)';ctx.lineWidth=isAccent?.9:.65;ctx.beginPath();
  for(let i=0;i<=columns;i++){const p=points[j][i];if(i===0)ctx.moveTo(...p);else ctx.lineTo(...p);}ctx.stroke();
 }
 ctx.strokeStyle='rgba(125,139,115,.22)';ctx.lineWidth=.65;
 for(let i=0;i<=columns;i++){ctx.beginPath();for(let j=0;j<=rows;j++){const p=points[j][i];if(j===0)ctx.moveTo(...p);else ctx.lineTo(...p);}ctx.stroke();}
 const point=points[Math.round(rows*.59)][Math.round(columns*.77)];ctx.fillStyle='rgba(188,250,119,.85)';ctx.beginPath();ctx.arc(...point,2,0,Math.PI*2);ctx.fill();
}
function terrainLoop(now){terrainFrame=0;if(!motionEnabled||document.hidden)return;if(now-lastFrame>50){terrainTime+=Math.min((now-lastFrame)/1000,.1);lastFrame=now;drawTerrain();}terrainFrame=requestAnimationFrame(terrainLoop);}
function updateMotion(){
 if(terrainFrame){cancelAnimationFrame(terrainFrame);terrainFrame=0;}
 $('motion-toggle').setAttribute('aria-pressed',String(motionEnabled));$('motion-toggle').setAttribute('aria-label',motionEnabled?'Turn background motion off':'Turn background motion on');
 if(motionEnabled&&!document.hidden){lastFrame=performance.now();terrainFrame=requestAnimationFrame(terrainLoop);}else drawTerrain();
}
$('motion-toggle').addEventListener('click',()=>{motionEnabled=!motionEnabled;sessionStorage.setItem('receipts-motion',motionEnabled?'on':'off');updateMotion();});
motionQuery.addEventListener('change',event=>{motionEnabled=!event.matches;updateMotion();});
document.addEventListener('visibilitychange',updateMotion);
window.addEventListener('pointermove',event=>{if(!motionEnabled||event.pointerType==='touch')return;targetPointerX=event.clientX/innerWidth-.5;targetPointerY=event.clientY/innerHeight-.5;},{passive:true});
window.addEventListener('resize',resizeTerrain);resizeTerrain();updateMotion();
