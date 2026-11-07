'use strict';

let companyDirectory=new CompanyDirectory.Directory(Object.entries(names).map(([ticker,name])=>({ticker,name,featured:true})));
let companyDirectoryLoaded=false;
const lookupControls=[];
function rememberCompany(company){if(company)names[company.ticker]=company.name;return company;}
const companyDirectoryReady=fetch('/static/companies.json').then(response=>{if(!response.ok)throw new Error('Directory unavailable');return response.json();}).then(data=>{
 companyDirectory=new CompanyDirectory.Directory(data.companies);companyDirectoryLoaded=true;
 for(const control of lookupControls)control.refresh();
 decorateCompanyCases();updateSelectedCompany();
}).catch(()=>{decorateCompanyCases();});

function companyLogo(company){
 const logo=el('span',(company?.ticker||'?').replace(/[^A-Z0-9]/g,'').slice(0,2),'company-logo');logo.setAttribute('aria-hidden','true');
 if(company?.logo){
  const image=document.createElement('img');image.alt='';image.src=company.logo;image.decoding='async';
  image.addEventListener('load',()=>logo.classList.add('logo-loaded'));
  image.addEventListener('error',()=>image.remove());logo.append(image);
 }
 return logo;
}
function decorateCompanyCases(){
 const featured={Automakers:['TSLA'],Semiconductors:['NVDA'],'Cloud platforms':['MSFT','AMZN','GOOGL']};
 for(const button of document.querySelectorAll('.case-card')){
  button.querySelector('.case-logos')?.remove();const group=el('span',null,'case-logos');group.setAttribute('aria-hidden','true');
  for(const ticker of featured[button.dataset.case]||[])group.append(companyLogo(companyDirectory.symbols.get(ticker)));
  button.prepend(group);
 }
}
function updateSelectedCompany(){
 const company=companyDirectory.resolve($('tickers').value),target=$('selected-company');
 target.replaceChildren();target.hidden=!company;
 if(company){rememberCompany(company);target.append(companyLogo(company),el('span',company.name),el('span',company.ticker,'selected-ticker'));}
}
function attachCompanyLookup(input,popup,{main=false}={}){
 let matches=[],active=-1,selected=null;
 input.removeAttribute('list');input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');input.setAttribute('aria-controls',popup.id);input.setAttribute('spellcheck','false');
 function close(){popup.hidden=true;active=-1;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');}
 function highlight(index){active=index;const options=popup.querySelectorAll('[role=option]');options.forEach((option,i)=>option.setAttribute('aria-selected',String(i===active)));if(options[active]){input.setAttribute('aria-activedescendant',options[active].id);options[active].scrollIntoView({block:'nearest'});}else input.removeAttribute('aria-activedescendant');}
 function choose(company){
  selected=company;rememberCompany(company);input.value=main?company.name:company.ticker;input.setCustomValidity('');close();
  if(main){const icon=document.querySelector('.search-icon');icon.setAttribute('hidden','');$('search-company-logo').replaceChildren(companyLogo(company));$('search-company-logo').hidden=false;}
  else{updateSelectedCompany();updateCompanyQuestion();updateScopeCaption();}
  $('lookup-announcement').textContent=`Selected ${company.name}, ${company.ticker}.`;input.focus();
 }
 function refresh(){
  if(document.activeElement!==input||state.busy)return;
  const query=input.value.trim();matches=companyDirectory.search(query);active=-1;popup.replaceChildren();
  // Full research questions remain free text, without a distracting empty menu.
  if(main&&query.length>70||main&&/[?]/.test(query)){close();return;}
  for(const [index,company]of matches.entries()){
   const option=el('div',null,'company-option');option.id=popup.id+'-'+index;option.setAttribute('role','option');option.setAttribute('aria-selected','false');
   const label=el('span',null,'company-option-label');label.append(el('span',company.name,'company-option-name'),el('span',company.ticker,'company-option-ticker'));
   option.append(companyLogo(company),label);option.addEventListener('pointerdown',event=>event.preventDefault());option.addEventListener('click',()=>{if(!state.busy)choose(company);});popup.append(option);
  }
  if(!matches.length){const message=companyDirectoryLoaded?'No matching company. Try another name or U.S. ticker.':'Company directory is unavailable. You can still enter a U.S. ticker.';popup.append(el('div',message,'lookup-empty'));}
  popup.hidden=false;input.setAttribute('aria-expanded','true');input.removeAttribute('aria-activedescendant');
 }
 input.addEventListener('input',()=>{selected=null;input.setCustomValidity('');$('lookup-announcement').textContent='';if(main){document.querySelector('.search-icon').removeAttribute('hidden');$('search-company-logo').hidden=true;}else updateSelectedCompany();refresh();});
 input.addEventListener('focus',refresh);
 input.addEventListener('keydown',event=>{
  if(event.isComposing)return;
  if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();if(popup.hidden)refresh();if(matches.length)highlight(active<0?(event.key==='ArrowDown'?0:matches.length-1):(active+(event.key==='ArrowDown'?1:-1)+matches.length)%matches.length);}
  else if(event.key==='Enter'&&!popup.hidden&&active>=0){event.preventDefault();choose(matches[active]);}
  else if(event.key==='Escape'&&!popup.hidden){event.preventDefault();event.stopPropagation();close();}
  else if(event.key==='Tab')close();
 });
 input.addEventListener('blur',close);
 document.addEventListener('pointerdown',event=>{if(!input.contains(event.target)&&!popup.contains(event.target))close();});
 const control={refresh,close,getSelection:()=>selected&&input.value===(main?selected.name:selected.ticker)?selected:null};lookupControls.push(control);return control;
}
const mainCompanyLookup=attachCompanyLookup($('company-search'),$('company-suggestions'),{main:true});
attachCompanyLookup($('tickers'),$('research-company-suggestions'));
$('research-dialog').addEventListener('close',()=>lookupControls.forEach(control=>control.close()));
$('tickers').addEventListener('change',updateSelectedCompany);
decorateCompanyCases();updateSelectedCompany();
