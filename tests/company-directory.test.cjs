const assert=require('node:assert/strict');
const {test}=require('node:test');
const {Directory}=require('../static/company-directory.js');
const {companies}=require('../static/companies.json');
const directory=new Directory(companies);
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
