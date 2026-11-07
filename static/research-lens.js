'use strict';

const LensDates=(()=>{
 const iso=date=>date.toISOString().slice(0,10);
 function validISO(value,max='9999-12-31'){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||value<'2012-01-01'||value>max)return false;
  const date=new Date(value+'T12:00:00Z');return !Number.isNaN(date.getTime())&&iso(date)===value;
 }
 const addDays=(value,days)=>{const date=new Date(value+'T12:00:00Z');date.setUTCDate(date.getUTCDate()+days);return iso(date);};
 return {validISO,addDays,iso};
})();
if(typeof module!=='undefined')module.exports=LensDates;

if(typeof document!=='undefined'){
 const calendar=$('lens-calendar');let input=null,trigger=null,month=null;
 function close(){calendar.hidden=true;trigger?.setAttribute('aria-expanded','false');}
 function place(){if(!trigger)return;const rect=trigger.closest('.date-entry').getBoundingClientRect(),width=280,height=calendar.getBoundingClientRect().height;if(rect.bottom<0||rect.top>innerHeight){close();return;}calendar.style.left=Math.max(12,Math.min(innerWidth-width-12,rect.left))+'px';calendar.style.top=Math.max(12,rect.bottom+8+height<innerHeight?rect.bottom+8:rect.top-height-8)+'px';}
 function arrow(label,path,action){const button=el('button',null,'calendar-nav');button.type='button';button.setAttribute('aria-label',label);const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 20 20');const line=document.createElementNS(svg.namespaceURI,'path');line.setAttribute('d',path);svg.append(line);button.append(svg);button.addEventListener('click',action);return button;}
 function render(focusDate=null){
  calendar.replaceChildren();
  const header=el('div',null,'calendar-heading');
  const previous=arrow('Previous month','M12 4 6 10l6 6',()=>{month.setUTCMonth(month.getUTCMonth()-1);render();}),next=arrow('Next month','M8 4l6 6-6 6',()=>{month.setUTCMonth(month.getUTCMonth()+1);render();});previous.disabled=LensDates.iso(month)<='2012-01-01';next.disabled=LensDates.iso(new Date(Date.UTC(month.getUTCFullYear(),month.getUTCMonth()+1,1,12)))>input.max;header.append(previous,el('span',month.toLocaleDateString('en-US',{month:'long',year:'numeric',timeZone:'UTC'})),next);calendar.append(header);
  const weekdays=el('div',null,'calendar-weekdays');for(const day of ['M','T','W','T','F','S','S'])weekdays.append(el('span',day));calendar.append(weekdays);
  const days=el('div',null,'calendar-days');days.setAttribute('role','group');days.setAttribute('aria-label','Days in this month');
  const offset=(month.getUTCDay()+6)%7,count=new Date(Date.UTC(month.getUTCFullYear(),month.getUTCMonth()+1,0)).getUTCDate();
  for(let i=0;i<offset;i++){const space=el('span');space.setAttribute('aria-hidden','true');days.append(space);}
  for(let day=1;day<=count;day++){
   const date=new Date(Date.UTC(month.getUTCFullYear(),month.getUTCMonth(),day,12)),value=LensDates.iso(date),button=el('button',String(day),'calendar-day');button.type='button';button.dataset.date=value;button.setAttribute('aria-label',date.toLocaleDateString('en-US',{dateStyle:'full',timeZone:'UTC'}));button.setAttribute('aria-pressed',String(input.value===value));button.disabled=!LensDates.validISO(value,input.max);button.tabIndex=value===(focusDate||input.value)?0:-1;
   button.addEventListener('click',()=>{input.value=value;input.setCustomValidity('');input.dispatchEvent(new Event('change',{bubbles:true}));close();input.focus();});
   button.addEventListener('keydown',event=>{
    const delta={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[event.key];if(!delta)return;event.preventDefault();const next=LensDates.addDays(value,delta);if(!LensDates.validISO(next,input.max))return;month=new Date(next.slice(0,7)+'-01T12:00:00Z');render(next);
   });days.append(button);
  }
  calendar.append(days);
  if(!days.querySelector('button[tabindex="0"]')){const first=days.querySelector('button:not(:disabled)');if(first)first.tabIndex=0;}
  if(!calendar.hidden)place();
  if(focusDate)days.querySelector('[data-date="'+focusDate+'"]')?.focus();
 }
 for(const button of document.querySelectorAll('[data-calendar-for]'))button.addEventListener('click',event=>{
  event.preventDefault();const same=trigger===button&&!calendar.hidden;close();if(same)return;
  trigger=button;input=$(button.dataset.calendarFor);const value=LensDates.validISO(input.value,input.max)?input.value:input.max;
  month=new Date(value.slice(0,7)+'-01T12:00:00Z');render();calendar.hidden=false;button.setAttribute('aria-expanded','true');
  place();calendar.querySelector('button[tabindex="0"]')?.focus();
 });
 for(const id of ['start','asof','through'])$(id).addEventListener('input',()=>{const field=$(id),digits=field.value.replace(/\D/g,'').slice(0,8);field.value=digits.slice(0,4)+(digits.length>4?'-'+digits.slice(4,6):'')+(digits.length>6?'-'+digits.slice(6):'');field.setCustomValidity('');});
 document.addEventListener('pointerdown',event=>{if(!calendar.contains(event.target)&&!event.target.closest('[data-calendar-for]'))close();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!calendar.hidden){event.preventDefault();close();trigger?.focus();}});
 window.addEventListener('resize',close);window.addEventListener('scroll',()=>{if(!calendar.hidden)place();},{passive:true});
}
