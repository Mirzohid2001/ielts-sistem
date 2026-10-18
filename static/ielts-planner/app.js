import {createAccountStore} from './account-store.js';
import {applyResourceRoutes} from './resource-routes.js';
import {showLoadFailure,showSaveRecovery} from './account-ui.js';
import {t,MONTHS} from './i18n.js';
import {SKILLS,DAY_NAMES,DAY_SHORT,RESOURCE,dateString,parseDate,addDays,dayIndex,diffDays,monday,overall,timeMinutes,timeString,defaultProfile,validateProfile,phaseFor,generatePlan,weekDates,validateTaskEdit,refreshPlanContent,makeLesson,CONTENT_VERSION,DAILY_MINUTES} from './planner.js';
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const ICONS={
 'lock':'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
 'check':'<path d="m5 12 4 4L19 6"/>',
 'calendar':'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18m-13 4h1m6 0h1m-8 3h1"/>',
 'spark':'<path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Zm7-1v4m-2-2h4"/>',
 'arrow-up':'<path d="M5 17 17 5M5 5h12v12"/>',
 'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
 'chevron-left':'<path d="m15 6-6 6 6 6"/>',
 'chevron-right':'<path d="m9 6 6 6-6 6"/>',
 'external':'<path d="M14 3h7v7m0-7-11 11M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
 'sliders':'<path d="M4 7h7m4 0h5M4 17h3m4 0h9"/><circle cx="13" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
 'info':'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.01"/>',
 'download':'<path d="M12 3v12m-5-5 5 5 5-5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',
 'list':'<path d="M9 6h12M9 12h12M9 18h12M3 6h.01M3 12h.01M3 18h.01"/>',
 'clock':'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 'target':'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
 'play':'<rect x="3" y="3" width="18" height="18" rx="4"/><path d="m10 8 6 4-6 4V8Z"/>',
 'book':'<path d="M12 5v16m0-16C8 2 3 3 3 3v15s5-1 9 3c4-4 9-3 9-3V3s-5-1-9 2Z"/>',
 'close':'<path d="m6 6 12 12M6 18 18 6"/>',
};
function icon(name){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]||ICONS.info}</svg>`;}
function icons(root=document){root.querySelectorAll('[data-icon]').forEach(e=>{e.innerHTML=icon(e.dataset.icon);});}
function escape(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function formatDate(s,year=false){const d=parseDate(s);return `${d.getDate()}-${MONTHS[d.getMonth()]}${year?`, ${d.getFullYear()}`:''}`;}
function formatMinutes(n){return n>=60?`${Math.floor(n/60)} ${t('soat')}${n%60?' '+n%60+' '+t('daq'):''}`:`${n} ${t('daq')}`;}
applyResourceRoutes(RESOURCE);
const accountStore=createAccountStore({endpoint:document.querySelector('[data-planner-api]')?.dataset.plannerApi||'/ielts/rejam/api/'});
let saved=null,storageError=false;
document.body.inert=true;
try{saved=await accountStore.load();if(saved!==null&&!validSaved(saved))throw new Error('INVALID_SAVED_PLAN');}
catch(error){showLoadFailure();throw error;}
document.body.inert=false;
function validSaved(s){return s&&s.version===1&&s.plan&&/^\d{4}-\d{2}-\d{2}$/.test(s.plan.startDate)&&s.plan.profile&&SKILLS.every(k=>Number.isFinite(s.plan.profile.scores?.[k]))&&Array.isArray(s.plan.profile.days)&&Array.isArray(s.plan.profile.weak)&&/^\d{4}-\d{2}-\d{2}$/.test(s.plan.profile.exam)&&diffDays(s.plan.startDate,s.plan.profile.exam)<=740&&Array.isArray(s.plan.tasks)&&s.plan.tasks.every(t=>typeof t.id==='string'&&SKILLS.includes(t.skill)&&RESOURCE[t.resource]&&Number.isFinite(t.duration)&&/^\d{4}-\d{2}-\d{2}$/.test(t.date)&&/^\d{2}:\d{2}$/.test(t.time)&&typeof t.title==='string'&&typeof t.description==='string');}
let isSample=!validSaved(saved);
let plan=isSample?generatePlan(defaultProfile()):saved.plan;
const contentUpdated=!isSample&&plan.contentVersion!==CONTENT_VERSION;
if(contentUpdated)plan=refreshPlanContent(plan);
let view=saved?.view==='calendar'?'calendar':'list';
function initialWeek(p){const next=p.tasks.find(t=>t.date>=dateString());return Math.max(0,weekDates(p).indexOf(monday(next?.date||dateString())));}
let week=initialWeek(plan),dayFilter='all',skillFilter='all',editingId=null,toastTimer;
function persist(){
  if(isSample)return false;
  accountStore.save({version:1,plan,view});
  updateSaveStatus();
  return true;
}
function adoptPersonal(){
  isSample=false;
  accountStore.save({version:1,plan,view});
  updateSaveStatus();
}
function requirePersonal(action=t('continue')){
  if(!isSample)return true;
  notify(t('needPersonal',{action}));
  $('#generate')?.scrollIntoView({block:'center',behavior:'smooth'});
  return false;
}
function updateSaveStatus(){
  const state=accountStore.state(),el=$('#save-status');
  el.innerHTML=icon(storageError?'info':isSample?'info':'check')+(storageError?t('saveFailed'):state.pending?t('saving'):isSample?t('sampleStatus'):t('savedStatus'));
  if(storageError){el.setAttribute('role','button');el.tabIndex=0;}else{el.removeAttribute('role');el.removeAttribute('tabindex');}
  $('#plan-type').textContent=isSample?t('planTypeSample'):t('planTypePersonal');
  $('#generate-label').textContent=isSample?t('generateSample'):t('generateUpdate');
  document.getElementById('planner-app')?.classList.toggle('is-sample',isSample);
}
function notify(message,error=false){clearTimeout(toastTimer);const el=$('#toast');el.textContent=message;el.classList.toggle('error',error);el.hidden=false;toastTimer=setTimeout(()=>el.hidden=true,4500);}
function fillForm(p){
  $('#score-inputs').innerHTML=SKILLS.map(s=>`<label class="score-label ${s}" for="score-${s}"><span><i class="skill-dot"></i>${s}</span><select id="score-${s}" data-score="${s}" aria-label="${escape(t('scoreAria',{skill:s}))}">${Array.from({length:19},(_,i)=>i/2).map(n=>`<option value="${n}" ${n===p.scores[s]?'selected':''}>${n.toFixed(1)}</option>`).join('')}</select></label>`).join('');
  $('#target').innerHTML=Array.from({length:17},(_,i)=>1+i/2).map(n=>`<option value="${n}" ${n===p.target?'selected':''}>${n.toFixed(1)}</option>`).join('');
  $('#exam').min=addDays(dateString(),1);$('#exam').max=addDays(dateString(),730);$('#exam').value=p.exam;
  $('#day-inputs').innerHTML=DAY_SHORT.map((name,i)=>`<button type="button" data-day="${i}" class="${p.days.includes(i)?'selected':''}" aria-pressed="${p.days.includes(i)}" aria-label="${DAY_NAMES[i]}">${name}</button>`).join('');
  $('#minutes').value=DAILY_MINUTES.find(n=>n>=p.minutes)||240;$('#start-time').value=p.time;
  $('#weak-inputs').innerHTML=SKILLS.map(s=>`<button type="button" data-weak="${s}" class="${s} ${p.weak.includes(s)?'selected':''}" aria-pressed="${p.weak.includes(s)}"><i class="skill-dot"></i>${s}${icon('check')}</button>`).join('');
  updateDraft();
}
function readForm(){return {scores:Object.fromEntries(SKILLS.map(s=>[s,Number($(`#score-${s}`).value)])),target:Number($('#target').value),exam:$('#exam').value,days:$$('[data-day][aria-pressed=true]').map(e=>Number(e.dataset.day)),minutes:Number($('#minutes').value),time:$('#start-time').value,weak:$$('[data-weak][aria-pressed=true]').map(e=>e.dataset.weak)};}
function updateDraft(){const p=readForm();$('#draft-overall').textContent=overall(p.scores).toFixed(1);}
function dirty(){updateDraft();$('#dirty-message').hidden=false;$('#form-error').hidden=true;}
$('#profile-form').addEventListener('click',e=>{const button=e.target.closest('[data-day],[data-weak]');if(!button)return;const on=button.getAttribute('aria-pressed')!=='true';button.setAttribute('aria-pressed',String(on));button.classList.toggle('selected',on);dirty();});
$('#profile-form').addEventListener('change',dirty);
$('#profile-form').addEventListener('submit',e=>{e.preventDefault();const p=readForm(),error=validateProfile(p);if(error){$('#form-error').textContent=error;$('#form-error').hidden=false;$('#form-error').scrollIntoView({block:'nearest',behavior:'smooth'});return;}
  const wasSample=isSample;
  plan=generatePlan(p,{previous:wasSample?null:plan});
  week=initialWeek(plan);dayFilter='all';skillFilter='all';$('#skill-filter').value='all';
  $('#form-error').hidden=true;$('#dirty-message').hidden=true;
  adoptPersonal();render();
  notify(wasSample?t('notifyCreated'):t('notifyUpdated'));
  $('.plan-workspace')?.scrollIntoView({behavior:'smooth',block:'start'});
});
$('#sample-banner-cta')?.addEventListener('click',()=>{
  $('#profile-form')?.scrollIntoView({behavior:'smooth',block:'start'});
  $('#generate')?.focus();
});
function currentTasks(){const start=weekDates(plan)[week],end=addDays(start,7);return plan.tasks.filter(t=>t.date>=start&&t.date<end);}
function render(){
  const p=plan.profile,today=dateString(),cur=overall(p.scores),gap=p.target-cur,daysLeft=Math.max(0,diffDays(today,p.exam));
  const ringDeg=Math.max(8,Math.min(360,Math.round((cur/Math.max(p.target,0.5))*360)));
  const ring=$('#hero-ring'); if(ring) ring.style.setProperty('--ring-deg',ringDeg+'deg');
  $('#hero-target').textContent=p.target.toFixed(1);
  $('#hero-current').innerHTML=`${cur.toFixed(1)} <small>${t('band')}</small>`;
  $('#hero-days').innerHTML=`${daysLeft} <small>${t('kun')}</small>`;
  $('#hero-exam').textContent=formatDate(p.exam,true);
  $('#hero-hours').textContent=t('perWeek',{time:formatMinutes(p.days.length*p.minutes)});
  const note=$('#hero-note');
  if(note) note.innerHTML=daysLeft<=0
    ? `${icon('info')}${t('examNeedUpdate')}`
    : gap<=0 ? `${icon('check')}${t('atGoal')}` : `${icon('arrow-up')}${t('gapLeft',{gap:gap.toFixed(1)})}`;
  const weeks=weekDates(plan);week=Math.min(Math.max(0,week),weeks.length-1);$('#week-select').innerHTML=weeks.map((d,i)=>`<option value="${i}" ${i===week?'selected':''}>${t('weekN',{n:i+1})}</option>`).join('');
  const start=weeks[week],end=addDays(start,6);$('#week-range').textContent=`${formatDate(start)} – ${formatDate(end)}`;$('#prev-week').disabled=week===0;$('#next-week').disabled=week===weeks.length-1;
  const tasks=currentTasks(),done=tasks.filter(t=>t.done).length,minutes=tasks.reduce((n,t)=>n+t.duration,0),days=new Set(tasks.map(t=>t.date)).size,progress=tasks.length?Math.round(done/tasks.length*100):0;
  const phase=phaseFor(tasks[0]?.date||start,plan.generatedAt||plan.startDate,p.exam);$('#phase-badge').textContent=phase.name;$('#week-load').textContent=t('weekLoad',{days,time:formatMinutes(minutes)});$('#week-complete').textContent=t('weekDone',{done,total:tasks.length});$('#week-progress').setAttribute('aria-valuenow',progress);$('#week-progress>span').style.width=progress+'%';
  const setText=(sel,val)=>{const el=$(sel);if(el)el.textContent=val;};
  setText('#stat-overall',cur.toFixed(1));
  setText('#stat-gap',(gap>=0?'+':'')+gap.toFixed(1));
  setText('#stat-days',String(daysLeft));
  setText('#stat-week',`${done}/${tasks.length}`);
  $('#list-view').classList.toggle('selected',view==='list');$('#calendar-view').classList.toggle('selected',view==='calendar');$('#list-view').setAttribute('aria-pressed',String(view==='list'));$('#calendar-view').setAttribute('aria-pressed',String(view==='calendar'));
  $('#day-filter').innerHTML=[['all',t('all')],...DAY_SHORT.map((n,i)=>[String(i),n])].map(([value,name])=>`<button data-filter="${value}" class="${dayFilter===value?'active':''}" aria-pressed="${dayFilter===value}">${name}</button>`).join('');
  $('#day-filter').hidden=view==='calendar';
  const filtered=tasks.filter(t=>(view==='calendar'||dayFilter==='all'||String(dayIndex(t.date))===dayFilter)&&(skillFilter==='all'||t.skill===skillFilter));
  $('#task-content').innerHTML=view==='calendar'?renderCalendar(start,filtered):renderList(filtered);
  const totals=Object.fromEntries(SKILLS.map(s=>[s,tasks.filter(t=>t.skill===s).reduce((n,t)=>n+t.duration,0)]));
  const ranked=[...SKILLS].sort((a,b)=>totals[b]-totals[a]);
  const nextOpen=tasks.find(t=>!t.done&&t.date>=today)||tasks.find(t=>!t.done);
  $('#focus-description').textContent=nextOpen
    ? t('nextStep',{title:nextOpen.title,when:`${formatDate(nextOpen.date)} ${nextOpen.time}`})
    : (minutes?t('focusMore',{skills:ranked.slice(0,2).join(` ${t('and')} `)}):t('noTasksWeek'));
  $('#skill-distribution').innerHTML=SKILLS.map(s=>`<div class="skill-meter ${s}"><label>${s}<strong>${totals[s]} ${t('daq')}</strong></label><div><span style="width:${minutes?totals[s]/minutes*100:0}%"></span></div></div>`).join('');
  $('#plan-advice').textContent=daysLeft<=0?t('advicePast'):gap<=0?t('adviceAtGoal'):gap>=1.5&&daysLeft<42?t('adviceTight'):t('adviceDefault',{tail:daysLeft<=7?t('adviceLastWeek'):t('adviceNoGuarantee')});
  const banner=$('#sample-banner'); if(banner) banner.hidden=!isSample;
  updateSaveStatus();
}
function renderList(tasks){
  if(!tasks.length)return `<div class="empty-state">${icon('calendar')}${t('emptyDay')}<p>${t('emptyDayHint')}</p></div>`;
  const dates=[...new Set(tasks.map(t=>t.date))].sort();
  return dates.map(date=>{const dayTasks=tasks.filter(t=>t.date===date).sort((a,b)=>a.time.localeCompare(b.time));return `<div class="day-group"><div class="day-heading"><h4>${DAY_NAMES[dayIndex(date)]}</h4><span>${formatDate(date)}</span>${date===dateString()?`<span class="day-today">${t('today')}</span>`:''}${date<dateString()&&dayTasks.some(t=>!t.done)?`<span>${t('pastDay')}</span>`:''}<small>${formatMinutes(dayTasks.reduce((n,t)=>n+t.duration,0))}</small></div>${dayTasks.map(trow=>`<article class="task-row ${trow.skill} ${trow.done?'done':''} ${trow.date===dateString()&&!trow.done?'is-today':''}"><label class="task-check"><input type="checkbox" data-complete="${escape(trow.id)}" ${trow.done?'checked':''} aria-label="${escape(t('doneAria',{title:trow.title}))}"></label><button class="task-main" data-task="${escape(trow.id)}"><strong>${escape(trow.title)}</strong><span class="task-meta">${icon('clock')}${trow.time}<span>·</span>${escape(RESOURCE[trow.resource].short||RESOURCE[trow.resource].name)}</span></button><span class="skill-badge">${trow.skill}</span><span class="task-duration">${icon('clock')}${trow.duration} ${t('daq')}</span><button class="task-arrow" data-task="${escape(trow.id)}" aria-label="${escape(t('editAria',{title:trow.title}))}">${icon('chevron-right')}</button></article>`).join('')}</div>`;}).join('');
}
function renderCalendar(start,tasks){
  return `<div class="calendar-scroll" tabindex="0" role="region" aria-label="${escape(t('calAria'))}"><div class="calendar-grid">${Array.from({length:7},(_,i)=>{const date=addDays(start,i),dayTasks=tasks.filter(x=>x.date===date).sort((a,b)=>a.time.localeCompare(b.time)),today=date===dateString();return `<div class="calendar-day ${today?'today':''}"><h4>${DAY_NAMES[i]}<span>${parseDate(date).getDate()}</span>${today?`<small>${t('today')}</small>`:''}</h4>${dayTasks.length?dayTasks.map(trow=>`<div class="calendar-task ${trow.skill} ${trow.done?'done':''}"><button data-task="${escape(trow.id)}"><time>${trow.time}–${timeString(timeMinutes(trow.time)+trow.duration)}</time><strong>${escape(trow.title)}</strong><small>${trow.skill} · ${trow.duration} ${t('daq')}</small></button><label><input type="checkbox" data-complete="${escape(trow.id)}" ${trow.done?'checked':''} aria-label="${escape(t('doneAria',{title:trow.title}))}">${t('done')}</label></div>`).join(''):`<div class="calendar-rest">${date===plan.profile.exam?`${t('examDay')}<br>${t('goodLuck')}`:date>plan.profile.exam?t('afterExam'):plan.profile.days.includes(i)?t('noTask'):`${t('restDay')}<br>${t('restHint')}`}</div>`}</div>`;}).join('')}</div></div><p class="calendar-hint">${icon('arrow-right')}${t('calHint')}</p>`;
}
$('#prev-week').addEventListener('click',()=>{week--;dayFilter='all';render();});$('#next-week').addEventListener('click',()=>{week++;dayFilter='all';render();});$('#week-select').addEventListener('change',e=>{week=Number(e.target.value);dayFilter='all';render();});
$('#day-filter').addEventListener('click',e=>{const b=e.target.closest('[data-filter]');if(b){dayFilter=b.dataset.filter;render();}});
$('#skill-filter').addEventListener('change',e=>{skillFilter=e.target.value;render();});
for(const v of ['list','calendar'])$(`#${v}-view`).addEventListener('click',()=>{view=v;persist();render();});
$('#task-content').addEventListener('change',e=>{
  if(!e.target.matches('[data-complete]'))return;
  const input=e.target,task=plan.tasks.find(t=>t.id===input.dataset.complete);
  if(!task)return;
  if(!requirePersonal(t('markTask'))){input.checked=task.done;return;}
  task.done=input.checked;persist();render();
  notify(task.done?t('notifyDone'):t('notifyUndone'));
});
$('#task-content').addEventListener('click',e=>{const b=e.target.closest('[data-task]');if(b)openTask(b.dataset.task);});
function openTask(id){
  const task=plan.tasks.find(t=>t.id===id);if(!task)return;
  editingId=id;
  $('#dialog-title').textContent=task.title;
  $('#dialog-description').textContent=task.description;
  renderTaskDetails(task);
  $('#dialog-skill').textContent=task.skill;
  $('#dialog-skill').className=`skill-badge ${task.skill}`;
  const resource=RESOURCE[task.resource];
  $('#dialog-resource').hidden=!resource.url;
  if(resource.url){
    $('#dialog-resource').href=resource.url;
    $('#dialog-resource').innerHTML=escape(resource.linkLabel||t('openInCabinet'))+icon('external');
  } else $('#dialog-resource').removeAttribute('href');
  $('#dialog-access').textContent=resource.access+(resource.url==='https://tonielts.uz/'?t('cabinetHint'):'');
  const today=dateString();
  $('#edit-date').value=task.date;
  $('#edit-date').min=task.date<today?task.date:today;
  $('#edit-date').max=addDays(plan.profile.exam,-1);
  $('#edit-time').value=task.time;
  $('#edit-duration').value=task.duration;
  $('#edit-error').hidden=true;
  const editLocked=isSample;
  $('#edit-date').disabled=editLocked;
  $('#edit-time').disabled=editLocked;
  $('#edit-duration').disabled=editLocked;
  const submitBtn=$('#task-edit-form button[type=submit]');
  if(submitBtn){submitBtn.disabled=editLocked;submitBtn.hidden=editLocked;}
  $('#task-dialog').showModal();
}
function closeDialog(){$('#task-dialog').close();editingId=null;}
$('#close-dialog').addEventListener('click',closeDialog);$('#cancel-edit').addEventListener('click',closeDialog);$('#task-dialog').addEventListener('click',e=>{if(e.target===$('#task-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeDialog();}});
$('#task-edit-form').addEventListener('submit',e=>{
  e.preventDefault();
  if(!requirePersonal(t('editTask')))return;
  const task=plan.tasks.find(t=>t.id===editingId);if(!task)return;
  const changes={date:$('#edit-date').value,time:$('#edit-time').value,duration:Number($('#edit-duration').value)};
  const error=validateTaskEdit(task,changes,plan);
  if(error){$('#edit-error').textContent=error;$('#edit-error').hidden=false;return;}
  const lesson=task.contentVersion===CONTENT_VERSION
    ? makeLesson(task.skill,task.lessonIndex,phaseFor(changes.date,plan.generatedAt||plan.startDate,plan.profile.exam),changes.duration)
    : {};
  Object.assign(task,lesson,changes);
  plan.tasks.sort((a,b)=>a.date.localeCompare(b.date)||a.time.localeCompare(b.time));
  week=Math.max(0,weekDates(plan).indexOf(monday(task.date)));
  dayFilter='all';skillFilter='all';$('#skill-filter').value='all';
  persist();closeDialog();render();notify(t('notifyRescheduled'));
});
$('#export').addEventListener('click',()=>{
  const tasks=currentTasks();if(!tasks.length){notify(t('exportEmpty'));return;}
  const icsEscape=s=>s.replace(/\\/g,'\\\\').replace(/\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;');
  const dateTime=(date,time)=>date.replaceAll('-','')+'T'+time.replace(':','')+'00';
  const timestamp=new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
  const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Ton Academy//IELTS Planner//UZ','CALSCALE:GREGORIAN',...tasks.flatMap(task=>['BEGIN:VEVENT',`UID:${task.id}@ton-ielts-planner`,`DTSTAMP:${timestamp}`,`DTSTART:${dateTime(task.date,task.time)}`,`DTEND:${dateTime(timeMinutes(task.time)+task.duration===1440?addDays(task.date,1):task.date,timeMinutes(task.time)+task.duration===1440?'00:00':timeString(timeMinutes(task.time)+task.duration))}`,`SUMMARY:${icsEscape(task.skill+': '+task.title)}`,`DESCRIPTION:${icsEscape([task.description,task.source,...(task.steps||[]).map(s=>s.minutes+' '+t('daq')+': '+s.text),task.outcome,task.checkpoint,task.ifStuck,task.reviewNext,RESOURCE[task.resource].url].filter(Boolean).join('\n'))}`,'END:VEVENT']),'END:VCALENDAR'];
  // Fold lines to 75 UTF-8 octets as required by iCalendar.
  const encoder=new TextEncoder();const folded=lines.map(line=>{let out='',chunk='',bytes=0;for(const c of line){const size=encoder.encode(c).length;if(bytes+size>75){out+=chunk+'\r\n';chunk=' ';bytes=1;}chunk+=c;bytes+=size;}return out+chunk;}).join('\r\n')+'\r\n';
  const blob=new Blob([folded],{type:'text/calendar;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`ton-ielts-${week+1}-${t('icsWeek')}.ics`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify(t('exportDone'));
});
function renderTaskDetails(task){
  $('#dialog-source-kind').textContent=RESOURCE[task.resource].selfStudy?t('sourceSelf'):t('sourceTon');
  $('#dialog-source').textContent=task.source||RESOURCE[task.resource].name;
  $('#dialog-steps').innerHTML=(task.steps||[]).map(step=>`<li><span class="step-time">${step.minutes} ${t('daq')}</span><span>${escape(step.text)}</span></li>`).join('');
  $('#dialog-steps').hidden=!task.steps?.length;
  $('#dialog-outcome').textContent=task.outcome||'';
  $('#dialog-outcome').hidden=!task.outcome;
  $('#dialog-checkpoint').textContent=task.checkpoint?t('checkpoint',{text:task.checkpoint}):'';
  $('#dialog-checkpoint').hidden=!task.checkpoint;
  $('#dialog-help-text').textContent=task.ifStuck||'';
  $('#dialog-review-next').textContent=task.reviewNext||'';
  $('#dialog-help').hidden=!task.ifStuck;
  $('#dialog-help').open=false;
}
accountStore.subscribe(state=>{storageError=!!state.error;updateSaveStatus();});
$('#save-status').addEventListener('click',()=>{if(storageError)showSaveRecovery(accountStore,{version:1,plan,view});});
$('#save-status').addEventListener('keydown',e=>{if(storageError&&['Enter',' '].includes(e.key)){e.preventDefault();showSaveRecovery(accountStore,{version:1,plan,view});}});
window.addEventListener('beforeunload',e=>{if(accountStore.state().pending){e.preventDefault();e.returnValue='';}});
fillForm(plan.profile);icons();render();
if(contentUpdated){
  persist();
  notify(t('contentUpdated'));
}
if(!isSample&&plan.profile.exam<=dateString()){
  $('#dirty-message').textContent=t('dirtyExamPast');
  $('#dirty-message').hidden=false;
  $('#exam').value=addDays(dateString(),56);
}
else if(!DAILY_MINUTES.includes(plan.profile.minutes)){
  $('#dirty-message').textContent=t('dirtyMinutes');
  $('#dirty-message').hidden=false;
}
if(isSample){
  $('#dirty-message').textContent=t('dirtySample');
  $('#dirty-message').hidden=false;
}
