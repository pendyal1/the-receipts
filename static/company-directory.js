'use strict';

// Shared by the browser and the small Node regression suite. No remote search API.
const CompanyDirectory=(()=>{
 const normalize=text=>String(text).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/&/g,' and ').replace(/[^a-z0-9]+/g,' ').trim();
 const canonical=text=>String(text).trim().replace(/^\$/,'').replace(/\./g,'-').toUpperCase();
 const distance=(a,b)=>{
  if(a.length===b.length){const differences=[...a].map((c,i)=>c===b[i]?-1:i).filter(i=>i>=0);if(differences.length===2&&differences[1]===differences[0]+1&&a[differences[0]]===b[differences[1]]&&a[differences[1]]===b[differences[0]])return 1;}
  const row=Array.from({length:b.length+1},(_,i)=>i);
  for(let i=1;i<=a.length;i++){let previous=row[0];row[0]=i;for(let j=1;j<=b.length;j++){const old=row[j];row[j]=Math.min(row[j]+1,row[j-1]+1,previous+(a[i-1]===b[j-1]?0:1));previous=old;}}
  return row[b.length];
 };
 class Directory{
  constructor(companies){
   this.companies=companies.map((company,index)=>({...company,order:index,terms:[company.name,...(company.aliases||[])].map(normalize)}));
   this.symbols=new Map(this.companies.map(c=>[c.ticker,c]));
  }
  resolve(text){
   const symbol=this.symbols.get(canonical(text));if(symbol)return symbol;
   const term=normalize(text);return term?this.companies.find(c=>c.terms.includes(term)):undefined;
  }
  search(text,limit=6){
   const q=normalize(text),symbol=canonical(text);
   if(!q)return this.companies.filter(c=>c.featured).slice(0,limit);
   if(q.length>100)return [];
   const exact=this.resolve(text),words=q.split(' '),ranked=[];
   for(const c of this.companies){
    let rank=c===exact?0:c.ticker.startsWith(symbol)?1:Infinity;
    for(const term of c.terms){
     if(term.startsWith(q)||term.replace(/ /g,'').startsWith(q.replace(/ /g,'')))rank=Math.min(rank,2);
     else if(words.every(word=>term.split(' ').some(part=>part.startsWith(word))))rank=Math.min(rank,3);
     else if(q.length>=3&&term.includes(q))rank=Math.min(rank,4);
    }
    if(Number.isFinite(rank))ranked.push({company:c,rank});
   }
   // Offer typo corrections only when ordinary prefix/word matching found nothing.
   if(!ranked.length&&q.length>=4&&q.length<=32){
    const allowed=q.length>7?2:1;
    for(const c of this.companies){
     const terms=[c.ticker.toLowerCase(),...c.terms,...c.terms.map(t=>t.split(' ')[0])];
     const d=Math.min(...terms.filter(t=>Math.abs(t.length-q.length)<=allowed).map(t=>distance(t,q)));
     if(d<=allowed)ranked.push({company:c,rank:5+d});
    }
   }
   return ranked.sort((a,b)=>a.rank-b.rank||Number(Boolean(b.company.featured))-Number(Boolean(a.company.featured))||a.company.order-b.company.order).slice(0,limit).map(r=>r.company);
  }
  mentions(text){
   const found=[],input=String(text),normalized=' '+normalize(text)+' ';
   const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
   for(const c of this.companies){
    // Ordinary words such as "a", "on" and "it" must never become stock tickers.
    const tickerPattern=escape(c.ticker).replace(/-/g,'[.-]');
    const tickerMatch=new RegExp('(?:^|[^A-Za-z0-9.-])\\$?('+tickerPattern+')(?=$|[^A-Za-z0-9.-])').exec(input);
    let index=tickerMatch?tickerMatch.index:Infinity;
    for(const term of c.terms){
     if(term.length<3)continue;
     const position=normalized.indexOf(' '+term+' ');
     if(position>=0)index=Math.min(index,position);
    }
    if(Number.isFinite(index))found.push({company:c,index});
   }
   // The directory contains multiple share classes with the same company name.
   // Keep explicit ticker choices; otherwise prefer the first class shown in lookup.
   const result=[],seen=new Set();
   const explicitCompanies=new Set(found.filter(item=>new RegExp('(?:^|[^A-Za-z0-9.-])\\$?'+escape(item.company.ticker).replace(/-/g,'[.-]')+'(?=$|[^A-Za-z0-9.-])').test(input)).map(item=>item.company.cik));
   for(const item of found.sort((a,b)=>a.index-b.index||a.company.order-b.company.order)){
    const explicit=new RegExp('(?:^|[^A-Za-z0-9.-])\\$?'+escape(item.company.ticker).replace(/-/g,'[.-]')+'(?=$|[^A-Za-z0-9.-])').test(input);
    if(!explicit&&explicitCompanies.has(item.company.cik))continue;
    const identity=explicit?item.company.ticker:String(item.company.cik||item.company.ticker);
    if(!seen.has(identity)){seen.add(identity);result.push(item.company);}
   }
   return result;
  }
 }
 return {Directory,normalize,canonical};
})();
if(typeof module!=='undefined')module.exports=CompanyDirectory;
