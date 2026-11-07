const assert=require('node:assert/strict');
const {test}=require('node:test');
const {Directory}=require('../static/company-directory.js');
const {companies}=require('../static/companies.json');
const directory=new Directory(companies);
const LensDates=require('../static/research-lens.js');
const symbols=text=>directory.mentions(text).map(c=>c.ticker);

test('tickers, aliases and share-class punctuation identify the actual company',()=>{
 for(const [input,ticker]of [['tsla','TSLA'],['$TSLA','TSLA'],['Google','GOOGL'],['Facebook','META'],['BRK.B','BRK-B'],['Coca Cola','KO'],['advanced micro devices','AMD']])assert.equal(directory.resolve(input)?.ticker,ticker,input);
 assert.equal(directory.resolve('not a real company'),undefined);
});
test('partial names, common typing mistakes and exact tickers rank sensibly',()=>{
 for(const [input,ticker]of [['Tes','TSLA'],['Tesal','TSLA'],['nvida','NVDA'],['micro soft','MSFT'],['Coca Cola','KO'],['F','F']])assert.equal(directory.search(input)[0]?.ticker,ticker,input);
 assert.equal(directory.search('zzzzzzzzzz').length,0);
 assert.equal(directory.search('<script>alert(1)</script>').length,0);
 assert.ok(directory.search('').length>0);
});
test('research questions preserve companies and explicit share classes',()=>{
 assert.deepEqual(symbols('Did Tesla outperform Ford and GM?'),['TSLA','F','GM']);
 assert.deepEqual(symbols('Compare Google (GOOG) with Microsoft'),['GOOG','MSFT']);
 assert.deepEqual(symbols('Did BRK.B grow?'),['BRK-B']);
 assert.deepEqual(symbols('Did Coca-Cola grow faster than PepsiCo?'),['KO','PEP']);
 assert.deepEqual(symbols('Is a company on track to meet its promises?'),[]);
 assert.equal(symbols('Compare Tesla, NVIDIA, Apple and Microsoft').length,4);
});
test('search extends beyond featured examples and cannot exceed its result cap',()=>{
 assert.equal(directory.resolve('PepsiCo, Inc.')?.ticker,'PEP');
 assert.ok(directory.search('bank',6).length<=6);
 assert.ok(companies.length>1000);
});
test('question-first submission detects companies and asks for only the missing decision',()=>{
 const plan=directory.prepareQuestion('Did Tesla outperform Ford and GM?');
 assert.equal(plan.status,'ready');assert.deepEqual(plan.companies.map(c=>c.ticker),['TSLA','F','GM']);
 assert.equal(directory.prepareQuestion('Did it deliver on its promises?').status,'needs_company');
 assert.equal(directory.prepareQuestion('Tesla').status,'needs_question');
 assert.equal(directory.prepareQuestion('   ').status,'empty');
 const picked=directory.prepareQuestion('Alphabet',{selected:directory.resolve('GOOG')});
 assert.equal(picked.companies[0].ticker,'GOOG');
});
test('optional company and peer choices preserve validation and never truncate extra peers',()=>{
 assert.equal(directory.prepareQuestion('Did it deliver?',{company:'Tesla'}).status,'ready');
 const plan=directory.prepareQuestion('Did Tesla deliver?',{peers:'General Motors, Ford'});
 assert.deepEqual(plan.companies.map(c=>c.ticker),['TSLA','GM','F']);
 assert.equal(directory.prepareQuestion('Did Tesla deliver?',{peers:'GM, F, NVIDIA'}).status,'too_many');
 assert.equal(directory.prepareQuestion('Did Tesla deliver?',{peers:'TSLA'}).status,'duplicate');
 assert.equal(directory.prepareQuestion('Did Tesla deliver?',{peers:'not a real company'}).status,'invalid_peer');
});
test('lowercase tickers work in questions while ordinary financial words do not become peers',()=>{
 assert.deepEqual(symbols('Compare tsla with nvda'),['TSLA','NVDA']);
 assert.deepEqual(symbols('How did NVIDIA benefit from AI demand and cash flow?'),['NVDA']);
 assert.deepEqual(symbols('Compare $AI and TSLA'),['AI','TSLA']);
 const source=require('node:fs').readFileSync(require('node:path').join(__dirname,'../static/app.js'),'utf8');
 const example=source.match(/'Consumer staples':\{tickers:'KO, PEP',question:'([^']+)'/)[1];
 assert.deepEqual(directory.prepareQuestion(example).companies.map(c=>c.ticker),['KO','PEP']);
});
test('custom dates reject impossible, future and out-of-coverage dates',()=>{
 assert.ok(LensDates.validISO('2024-02-29','2026-11-07'));
 for(const date of ['2023-02-29','2024-02-30','2026-11-08','2011-12-31','2023-2-3',''])assert.equal(LensDates.validISO(date,'2026-11-07'),false,date);
 assert.equal(LensDates.addDays('2024-02-28',1),'2024-02-29');
 assert.equal(LensDates.addDays('2023-12-31',1),'2024-01-01');
});
