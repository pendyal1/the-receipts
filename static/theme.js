'use strict';

// Set the saved palette before the stylesheet paints. Storage may be disabled.
(() => {
 const root=document.documentElement,key='receipts-theme';
 function apply(theme){
  root.dataset.theme=theme==='light'?'light':'dark';
  const light=root.dataset.theme==='light',button=document.getElementById('theme-toggle');
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',light?'#f1f3eb':'#080a09');
  if(button){
   const label=light?'Switch to dark mode':'Switch to light mode';
   button.setAttribute('aria-label',label);button.title=label;
   button.setAttribute('aria-pressed',String(light));
  }
  document.dispatchEvent(new Event('receipts-theme-change'));
 }
 let saved;try{saved=localStorage.getItem(key);}catch{}
 apply(saved);
 document.addEventListener('DOMContentLoaded',()=>{
  apply(root.dataset.theme);
  document.getElementById('theme-toggle').addEventListener('click',()=>{
   const theme=root.dataset.theme==='light'?'dark':'light';
   apply(theme);try{localStorage.setItem(key,theme);}catch{}
  });
 });
 window.addEventListener('storage',event=>{
  if(event.key===key||event.key===null)apply(event.newValue);
 });
})();
