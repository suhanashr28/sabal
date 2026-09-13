(() => {
 let settings, formatter, target, dayKey;
 const parts = now => Object.fromEntries(formatter.formatToParts(now).filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));
 // Convert midnight in the saved time zone to an actual instant (including DST).
 function midnight(year,month,day){const wall=Date.UTC(year,month-1,day);let instant=wall;for(let i=0;i<5;i++){const p=parts(new Date(instant));const adjustment=wall-Date.UTC(p.year,p.month-1,p.day,p.hour,p.minute,p.second);instant+=adjustment;if(!adjustment)break;}return instant;}
 function anniversary(year){const [,month,day]=settings.start_date.split('-').map(Number);return {month,day:Math.min(day,new Date(Date.UTC(year,month,0)).getUTCDate())};}
 function set(id,value){const el=document.getElementById(id);if(el&&el.textContent!==value)el.textContent=value;}
 function tick(){if(!settings||document.hidden)return;const now=new Date(),p=parts(now),key=`${p.year}-${p.month}-${p.day}`;
  if(dayKey!==key){dayKey=key;const [year,month,day]=settings.start_date.split('-').map(Number);const today=Date.UTC(p.year,p.month-1,p.day),start=Date.UTC(year,month-1,day);const a=anniversary(p.year);const isAnniversary=p.month===a.month&&p.day===a.day&&p.year>year;const years=Math.max(0,p.year-year-(p.month<a.month||(p.month===a.month&&p.day<a.day)?1:0));let nextYear=Math.max(year+1,p.year);let next=anniversary(nextYear);target=midnight(nextYear,next.month,next.day);if(target<=now.getTime()){nextYear++;next=anniversary(nextYear);target=midnight(nextYear,next.month,next.day);}
   set('relationship-days',Math.max(0,Math.floor((today-start)/86400000)).toLocaleString());set('relationship-years',isAnniversary?'Happy anniversary, my love! ♥':`${years} ${years===1?'year':'years'} of choosing you ♥`);set('relationship-next',`Counting down to ${nextYear-year} years together`);
   const time=document.querySelector('.relationship-counter time');time.dateTime=settings.start_date;time.textContent=new Date(start).toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
  }
  const seconds=Math.max(0,Math.ceil((target-now.getTime())/1000));set('love-days',String(Math.floor(seconds/86400)));set('love-hours',String(Math.floor(seconds/3600)%24).padStart(2,'0'));set('love-minutes',String(Math.floor(seconds/60)%60).padStart(2,'0'));set('love-seconds',String(seconds%60).padStart(2,'0'));
 }
 function configure(){if(!document.getElementById('relationship-days')||!LF.state)return;settings=LF.state.settings;formatter=new Intl.DateTimeFormat('en-GB',{timeZone:settings.timezone,year:'numeric',month:'numeric',day:'numeric',hour:'numeric',minute:'numeric',second:'numeric',hourCycle:'h23'});dayKey=null;tick();}
 LF.ready.then(configure);document.addEventListener('lf-state',configure);document.addEventListener('visibilitychange',tick);setInterval(tick,1000);
})();
