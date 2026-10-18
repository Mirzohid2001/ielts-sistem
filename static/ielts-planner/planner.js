export const DAILY_MINUTES = [60,90,120,150,180,210,240];
export const SKILLS = ['Listening', 'Reading', 'Writing', 'Speaking'];
import {DAY_NAMES,DAY_SHORT,t} from './i18n.js';
export {DAY_NAMES,DAY_SHORT};
import {RESOURCE,makeLesson,CONTENT_VERSION} from './curriculum.js';
export {RESOURCE,makeLesson,CONTENT_VERSION};
// Dates are local calendar dates; noon avoids DST boundary drift.
export function dateString(date = new Date()) { return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`; }
export function parseDate(s) { return new Date(`${s}T12:00:00`); }
export function addDays(s,n) { const d=parseDate(s); d.setDate(d.getDate()+n); return dateString(d); }
export function dayIndex(s) { return (parseDate(s).getDay()+6)%7; }
export function diffDays(a,b) { return Math.round((parseDate(b)-parseDate(a))/86400000); }
export function monday(s) { return addDays(s,-dayIndex(s)); }
export function overall(scores) { return Math.round(SKILLS.reduce((n,s)=>n+Number(scores[s]),0)/4*2)/2; }
export function timeMinutes(s) { const [h,m]=s.split(':').map(Number); return h*60+m; }
export function timeString(n) { return `${String(Math.floor(n/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}`; }
export function defaultProfile(today=dateString()) { return { scores:{Listening:6.5,Reading:6,Writing:5.5,Speaking:6}, target:7, exam:addDays(today,56), days:[0,1,3,4,5], minutes:60, time:'19:00', weak:['Writing','Speaking'] }; }
export function validateProfile(p,today=dateString()) {
  if (!p || !p.scores || SKILLS.some(s=>!Number.isFinite(p.scores[s])||p.scores[s]<0||p.scores[s]>9||p.scores[s]*2%1)) return t('errScores');
  if (!Number.isFinite(p.target)||p.target<1||p.target>9||p.target*2%1) return t('errTarget');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(p.exam)||!Number.isFinite(+parseDate(p.exam))||dateString(parseDate(p.exam))!==p.exam||p.exam<=today) return t('errExam');
  if (diffDays(today,p.exam)>730) return t('errExamRange');
  if (!Array.isArray(p.days)||!p.days.length||p.days.some(d=>!Number.isInteger(d)||d<0||d>6)) return t('errDays');
  if (!DAILY_MINUTES.includes(p.minutes)) return t('errMinutes');
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(p.time)||timeMinutes(p.time)+p.minutes>1440) return t('errTime');
  if (!Array.isArray(p.weak)||p.weak.some(s=>!SKILLS.includes(s))) return t('errWeak');
  let available=false;
  for(let d=today;d<p.exam;d=addDays(d,1)) if(p.days.includes(dayIndex(d))) {available=true;break;}
  if(!available) return t('errNoStudyDay');
  return '';
}
export function phaseFor(date,start,exam) {
  if(diffDays(date,exam)<=7) return {key:'review',name:t('phaseReview')};
  const ratio=diffDays(start,date)/Math.max(1,diffDays(start,exam));
  return ratio<.3 ? {key:'foundation',name:t('phaseFoundation')} : ratio<.75 ? {key:'practice',name:t('phasePractice')} : {key:'mock',name:t('phaseMock')};
}
export function refreshPlanContent(plan) {
  if(plan.contentVersion===CONTENT_VERSION)return plan;
  const indices=Object.fromEntries(SKILLS.map(s=>[s,0]));
  return {...plan,contentVersion:CONTENT_VERSION,tasks:plan.tasks.map(t=>{
    const index=indices[t.skill]++;
    if(t.done)return {...t};
    return {...t,...makeLesson(t.skill,index,phaseFor(t.date,plan.generatedAt||plan.startDate,plan.profile.exam),t.duration)};
  })};
}
export function generatePlan(p,{today=dateString(),previous=null}={}) {
  const error=validateProfile(p,today); if(error) throw new Error(error);
  // Keep completed work + overdue incomplete tasks; rebuild only from today forward.
  const history=(previous?.tasks||[])
    .filter(t=>t.done||t.date<today)
    .map(t=>({...t}));
  const tasks=[...history], weights={}, counts={}, indices={};
  SKILLS.forEach(s=>{weights[s]=1+Math.max(0,p.target-p.scores[s])*1.7+(p.weak.includes(s)?2:0);counts[s]=0;indices[s]=0;});
  for(let date=today;date<p.exam;date=addDays(date,1)) {
    if(!p.days.includes(dayIndex(date))) continue;
    const phase=phaseFor(date,today,p.exam);
    const keptToday=history.filter(t=>t.date===date);
    const capacity=phase.key==='review'?Math.min(p.minutes,60):p.minutes;
    let remaining=Math.max(0,capacity-keptToday.reduce((n,t)=>n+t.duration,0));
    let cursor=timeMinutes(p.time),slot=0;
    let previousSkill=keptToday.at(-1)?.skill;
    while(remaining>=15) {
      // Weighted fair allocation keeps stronger skills in the rotation too.
      const skill=[...SKILLS].sort((a,b)=>(counts[a]+30)/weights[a]-(counts[b]+30)/weights[b] || SKILLS.indexOf(a)-SKILLS.indexOf(b)).find(s=>s!==previousSkill)||SKILLS[0];
      const duration=Math.min(remaining,phase.key==='mock'&&remaining>=60&&['Writing','Reading','Listening'].includes(skill)?60:30);
      let conflict;
      do {conflict=keptToday.find(t=>cursor<timeMinutes(t.time)+t.duration&&cursor+duration>timeMinutes(t.time));if(conflict)cursor=timeMinutes(conflict.time)+conflict.duration;} while(conflict);
      if(cursor+duration>1440) break;
      const lesson=makeLesson(skill,indices[skill]++,phase,duration);
      const baseId=`${date}-${skill}-${slot++}`;
      let id=baseId,suffix=1;while(tasks.some(t=>t.id===id))id=`${baseId}-${suffix++}`;
      tasks.push({id,date,time:timeString(cursor),duration,skill,...lesson,done:false});
      cursor+=duration;remaining-=duration;counts[skill]+=duration;previousSkill=skill;
    }
  }
  tasks.sort((a,b)=>a.date.localeCompare(b.date)||a.time.localeCompare(b.time));
  const startDate=previous?.startDate&&previous.startDate<=today
    ? previous.startDate
    : (tasks[0]?.date||today);
  return {contentVersion:CONTENT_VERSION,profile:structuredClone(p),startDate,generatedAt:today,tasks};
}
export function weekDates(plan) {
  const dates=[];const start=monday(plan.startDate);const last=monday(addDays(plan.profile.exam,-1));
  for(let d=start;d<=last;d=addDays(d,7))dates.push(d);
  return dates.length?dates:[start];
}
export function validateTaskEdit(task,changes,plan,today=dateString()) {
  const {date,time,duration}=changes;
  if(task.minimumDuration&&duration<task.minimumDuration)return t('errMinDuration',{n:task.minimumDuration});
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||dateString(parseDate(date))!==date||date>=plan.profile.exam) {
    return t('errTaskDate');
  }
  // Keep original overdue date, or reschedule to today/future study days only.
  if(date!==task.date&&date<today) return t('errPastMove');
  if(date>=today&&!plan.profile.days.includes(dayIndex(date))) {
    return t('errNotStudyDay');
  }
  if(![15,30,45,60,90,120].includes(duration)||!/^([01]\d|2[0-3]):[0-5]\d$/.test(time)||timeMinutes(time)+duration>1440) {
    return t('errTimeDuration');
  }
  const others=plan.tasks.filter(t=>t.id!==task.id&&t.date===date);
  if(others.reduce((n,t)=>n+t.duration,0)+duration>plan.profile.minutes) {
    return t('errDayFull');
  }
  if(others.some(t=>timeMinutes(time)<timeMinutes(t.time)+t.duration&&timeMinutes(time)+duration>timeMinutes(t.time))) {
    return t('errOverlap');
  }
  return '';
}
