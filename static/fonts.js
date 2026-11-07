'use strict';

// Reveal text only after both self-hosted faces are available. No system stack.
Promise.resolve().then(()=>Promise.all([document.fonts.load('400 16px "Sora"'),document.fonts.load('600 16px "Orbitron"')])).then(faces=>{
 if(faces.some(face=>!face.length))throw new Error('Font did not load');
 document.documentElement.dataset.fontState='ready';
 document.getElementById('app-shell').hidden=false;
 document.dispatchEvent(new Event('receipts-fonts-ready'));
}).catch(()=>{
 document.documentElement.dataset.fontState='error';
 document.getElementById('font-loading').setAttribute('aria-label','Application fonts could not load. Retry loading the page.');
 document.getElementById('retry-fonts').hidden=false;
});
document.getElementById('retry-fonts').addEventListener('click',()=>location.reload());
