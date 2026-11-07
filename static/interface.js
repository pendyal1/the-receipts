'use strict';

// Interface copy is bundled; no source or user text is interpreted as markup.
const infoPanels={
 about:`<span class="section-index">01 — ABOUT THE APP</span><h2 id="info-title" class="info-title">The past has<br>a paper trail.</h2><p class="info-lead">For investors and traders who want to compare what a company said with what happened next.</p><div class="info-steps"><div class="info-step"><span>THEN</span><div><h3>What management expected.</h3><p>Return to the filings available at a historical date.</p></div></div><div class="info-step"><span>NEXT</span><div><h3>What the numbers revealed.</h3><p>Compare later financial results and industry peers.</p></div></div><div class="info-step"><span>PROOF</span><div><h3>Evidence you can open.</h3><p>Follow each citation back to the source record.</p></div></div></div><p class="info-small">Historical research, not trading recommendations. Built for Columbia · IEOR 4570.</p>`,
 how:`<span class="section-index">02 — A SHORT FIELD GUIDE</span><h2 id="info-title" class="info-title">Follow the evidence.</h2><div class="info-steps"><div class="info-step"><span>01</span><div><h3>Ask your question.</h3><p>Ask about a company’s past claims and later financial results. Press Enter to investigate; Shift+Enter adds a line.</p></div></div><div class="info-step"><span>02</span><div><h3>Add context if you want.</h3><p>Companies in your question are detected automatically. Open “Company, peers & dates” beneath the bar to adjust up to two peers or the historical window. The default is 2020–March 2025, with a March 1, 2023 viewpoint.</p></div></div><div class="info-step"><span>03</span><div><h3>Cross-examine the record.</h3><p>Read the finding, explore the chart, and open a numbered citation to inspect its evidence. Missing metrics and untestable claims are identified.</p></div></div></div><p class="info-small">Investigations usually take 1–3 minutes. “Browse source data only” opens the records without an AI report.</p>`,
 sources:`<span class="section-index">03 — THE PAPER TRAIL</span><h2 id="info-title" class="info-title">The Public Records.</h2><p class="info-lead">Three perspectives on the same company history.</p><div class="info-steps"><a class="source-row" href="https://www.sec.gov/edgar/search/" target="_blank" rel="noopener noreferrer"><div><strong>SEC EDGAR</strong><p>Management outlook in filings and reported annual financial metrics from XBRL.</p></div></a><a class="source-row" href="https://fred.stlouisfed.org/" target="_blank" rel="noopener noreferrer"><div><strong>FRED</strong><p>Interest rates and inflation for hindsight context. Revised series are not as-of observations.</p></div></a><a class="source-row" href="https://finance.yahoo.com/" target="_blank" rel="noopener noreferrer"><div><strong>Historical prices</strong><p>Vendor-adjusted closing prices via an unofficial Yahoo endpoint. Context, not proof of causation.</p></div></a></div><p class="info-small">Archived examples cover 2020–March 2025. Other companies and dates depend on live availability. Outlook excerpts are a bounded filing search; supported annual metrics cannot test every operational or segment-level claim.</p>`
};
function focusQuestion(){
 if($('info-dialog').open)$('info-dialog').close();
 if(state.busy)return;
 mainCompanyLookup.close();$('company-search').focus();
}
function openInfo(panel){
 if(!Object.hasOwn(infoPanels,panel))return;
 $('info-content').innerHTML=infoPanels[panel];
 $('info-dialog').querySelectorAll('[data-panel]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.panel===panel)));
 if(!$('info-dialog').open)$('info-dialog').showModal();
}
document.querySelectorAll('[data-panel]').forEach(button=>button.addEventListener('click',()=>openInfo(button.dataset.panel)));
document.querySelectorAll('[data-close-dialog]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
for(const dialog of document.querySelectorAll('dialog'))dialog.addEventListener('click',event=>{const r=dialog.getBoundingClientRect();if(event.target===dialog&&(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom))dialog.close();});
$('info-start').addEventListener('click',focusQuestion);

function sizeQuestionInput(){const input=$('company-search');input.style.height='0px';input.style.height=Math.min(156,Math.max(38,input.scrollHeight))+'px';}
function questionNotice(text,{settings=false,focus=null}={}){
 $('form-notice').textContent=text;$('form-notice').hidden=false;
 if(settings)$('research-settings').open=true;
 if(focus)$(focus).focus();
}
function fillQuestion(text){
 $('company-search').value=text;$('question').value=text;state.autoQuestion=null;
 $('form-notice').hidden=true;$('question-prompts').hidden=true;$('status').hidden=true;
 document.querySelector('.search-icon').removeAttribute('hidden');$('search-company-logo').hidden=true;
 mainCompanyLookup.close();sizeQuestionInput();$('company-search').focus();
}
function fillExample(example){
 if(state.busy)return;
 state.manualCompany=false;state.manualPeers=false;
 const symbols=example.tickers.split(',').map(t=>t.trim());$('tickers').value=symbols[0];$('peers').value=symbols.slice(1).join(', ');
 $('start').value='2020-01-01';$('asof').value='2023-03-01';$('through').value='2025-03-01';
 updateSelectedCompany();updateScopeCaption();fillQuestion(example.question);
}
async function submitQuestion(mode='chat'){
 if(state.busy)return;
 const text=$('company-search').value.trim();
 if(!text){$('company-search').setCustomValidity('Ask a historical financial question.');$('company-search').reportValidity();return;}
 await companyDirectoryReady;if(state.busy||text!==$('company-search').value.trim())return;
 const plan=companyDirectory.prepareQuestion(text,{selected:mainCompanyLookup.getSelection(),company:state.manualCompany?$('tickers').value:null,peers:state.manualPeers?$('peers').value:null});
 mainCompanyLookup.close();researchCompanyLookup.close();$('status').hidden=true;$('form-notice').hidden=true;$('question-prompts').hidden=true;
 if(plan.status==='needs_company'){if(!state.manualCompany){$('tickers').value='';updateSelectedCompany();}questionNotice('Which company should we investigate? Choose it below, then submit your question.',{settings:true,focus:'tickers'});return;}
 if(plan.status==='invalid_peer'){questionNotice('Choose a matching company name or U.S. ticker for each peer.',{settings:true,focus:'peers'});return;}
 if(plan.status==='too_many'){questionNotice('Research covers one company and up to two peers. Remove an extra company from your question.',{focus:'company-search'});return;}
 if(plan.status==='duplicate'){questionNotice('Choose different companies for the subject and its peers.',{settings:true,focus:'peers'});return;}
 plan.companies.forEach(rememberCompany);$('tickers').value=plan.companies[0].ticker;$('peers').value=plan.companies.slice(1).map(c=>c.ticker).join(', ');updateSelectedCompany();updateScopeCaption();
 if(plan.status==='needs_question'&&mode!=='evidence'){
  const company=plan.companies[0];questionNotice(`What would you like to know about ${company.name}? Ask a question or try one below.`);
  const prompts=$('question-prompts');prompts.replaceChildren();
  for(const question of [`Did ${company.name} deliver on its 2023 promises?`,`How did ${company.name}’s revenue change after 2022?`]){const button=el('button',question,'question-prompt');button.type='button';button.addEventListener('click',()=>fillQuestion(question));prompts.append(button);}
  prompts.hidden=false;return;
 }
 $('question').value=plan.status==='needs_question'?`Explore the historical financial records for ${plan.companies[0].name}.`:text;state.autoQuestion=null;
 await run(mode);
}
$('research-settings').addEventListener('toggle',async()=>{
 if(!$('research-settings').open||state.busy)return;
 await companyDirectoryReady;if(state.busy||!$('research-settings').open)return;
 const plan=companyDirectory.prepareQuestion($('company-search').value,{selected:mainCompanyLookup.getSelection(),company:state.manualCompany?$('tickers').value:null,peers:state.manualPeers?$('peers').value:null});
 if(!['ready','needs_question'].includes(plan.status))return;
 plan.companies.forEach(rememberCompany);
 if(!state.manualCompany)$('tickers').value=plan.companies[0].ticker;
 if(!state.manualPeers)$('peers').value=plan.companies.slice(1).map(c=>c.ticker).join(', ');
 updateSelectedCompany();updateScopeCaption();
});
$('research-form').addEventListener('submit',event=>{event.preventDefault();submitQuestion();});
$('preview').addEventListener('click',()=>submitQuestion('evidence'));
$('company-search').addEventListener('input',()=>{$('company-search').setCustomValidity('');$('form-notice').hidden=true;$('question-prompts').hidden=true;sizeQuestionInput();});
$('peers').addEventListener('input',()=>state.manualPeers=true);
$('tickers').addEventListener('change',()=>state.manualCompany=Boolean($('tickers').value.trim()));
sizeQuestionInput();

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
