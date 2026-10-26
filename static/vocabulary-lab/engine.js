import{bank}from'./data.js';
export const DAY=86400000;
export const normal=s=>String(s||'').toLowerCase().replace(/[’‘]/g,"'").replace(/[.,!?;:“”]/g,'').replace(/\s+/g,' ').trim();
export function emptyProgress(now=Date.now()){
 const metricKeys=['Precision','Collocations','Repetition Control','Academic Register','Lexical Flexibility','Word Families','Near-Synonyms','Naturalness','Recognition','Production'];
 return{version:1,level:'B2',count:6,mode:'Learn',items:{},metrics:Object.fromEntries(metricKeys.map(k=>[k,{ok:0,n:0}])),history:[],session:null,plan:{date:new Date(now).toDateString(),budget:30,heavy:false,done:[]},events:[],writingDraft:'',itemDrafts:{},created:now};
}
export function seed(now=Date.now()){
 const items={};const freshPhrases=['place emphasis on','academic performance','address an issue','contribute to','long-term consequences','place pressure on'];bank.filter(x=>!freshPhrases.includes(x.phrase)).forEach((x,i)=>{if(i<75)items[x.id]={status:i<34?'MASTERED':i<41?'USED':'LEARNING',recognition:{ok: i<34?9:4,n:i<34?10:5},production:{ok:i<34?8:2,n:i<34?9:4},recalls:i<41?4:0,uses:i<41?3:0,successDays:i<34?[now-20*DAY,now-12*DAY,now-5*DAY].map(d=>new Date(d).toISOString().slice(0,10)):[],interval:i<34?21:1,due:now+(i>=34&&i<41?-DAY:(i<34?14:2)*DAY),last:now-2*DAY,lapses:0,reviewCount:i<34?6:0,reviewStreak:i<34?6:0,first:now-25*DAY};});
 return{...emptyProgress(now),items,metrics:Object.fromEntries(Object.entries({'Precision':58,'Collocations':61,'Repetition Control':71,'Academic Register':76,'Lexical Flexibility':67,'Word Families':69,'Near-Synonyms':64,'Naturalness':65,'Recognition':82,'Production':55}).map(([k,v])=>[k,{ok:v,n:100}]))};
}
export function validProgress(s){return !!(s&&s.version===1&&s.items&&typeof s.items==='object'&&s.metrics&&typeof s.metrics==='object'&&s.plan&&Array.isArray(s.history));}
export function freshItem(now=Date.now()){return{status:'NEW',recognition:{ok:0,n:0},production:{ok:0,n:0},recalls:0,uses:0,successDays:[],interval:0,due:now,last:null,lapses:0,reviewCount:0,reviewStreak:0,first:now};}
export function accuracy(m){return m?.n?Math.round(m.ok/m.n*100):0;}
export function recordMetric(s,key,ok){s.metrics[key]??={ok:0,n:0};s.metrics[key].n++;if(ok)s.metrics[key].ok++;}
export function recordItem(s,id,type,ok,{review=false,now=Date.now(),eventId=null}={}){
 if(eventId&&s.events.includes(eventId))return;
 if(eventId)s.events.push(eventId);
 const p=s.items[id]??=freshItem(now);const recognition=['meaning','recognition','collocation'].includes(type);const bucket=recognition?'recognition':'production';p[bucket].n++;if(ok)p[bucket].ok++;
 recordMetric(s,recognition?'Recognition':'Production',ok);p.last=now;
 if(ok){if(!recognition)p.recalls+=type==='recall'?1:0;if(['free','transfer'].includes(type))p.uses++;
 const ranks=['NEW','LEARNING','RECOGNISED','RECALLED','USED','MASTERED'];const next=recognition?'RECOGNISED':type==='recall'?'RECALLED':'USED';if(ranks.indexOf(next)>ranks.indexOf(p.status))p.status=next;
 }else{p.lapses++;p.reviewStreak=0;p.status=p.status==='NEW'?'LEARNING':p.status==='MASTERED'?'USED':p.status;}
 if(review){p.reviewCount++;p.reviewStreak=ok?(p.reviewStreak||0)+1:0;const day=new Date(now).toISOString().slice(0,10);if(ok&&!p.successDays.includes(day))p.successDays.push(day);p.interval=ok?Math.min(45,Math.max(1,Math.round((p.interval||.5)*2.2))):.15;p.due=now+p.interval*DAY;}
 else if(!p.interval){p.interval=1;p.due=now+DAY;}
 if(ok&&p.reviewStreak>=3&&p.successDays.length>=3&&now-p.first>=14*DAY&&p.recalls>=3&&p.uses>=2&&accuracy(p.recognition)>=80&&accuracy(p.production)>=80)p.status='MASTERED';
}
export function dueItems(s,now=Date.now()){return bank.filter(x=>s.items[x.id]?.due<=now).sort((a,b)=>{const score=x=>{let p=s.items[x.id];return(now-p.due)/DAY+p.lapses*2+(100-accuracy(p.production))/20+(p.uses?0:4)+(p.status==='MASTERED'?-6:0);};return score(b)-score(a);});}
export function reviewType(s,item){const p=s.items[item.id];const types=['meaning','collocation','recall','controlled','free','transfer'];if(accuracy(p.recognition)>accuracy(p.production)+20)return ['recall','controlled','free','transfer'][p.reviewCount%4];return types[p.reviewCount%types.length];}
export function planTasks(s){const minutes=Math.max(0,s.plan.budget);if(minutes<5)return[];if(s.plan.heavy)return[{id:'review',title:'Review vocabulary',description:'Due items · focused recall',minutes:5}];const tasks=[{id:'learn',title:'Learn new vocabulary',description:`${s.count} expressions · ${s.level} · Education`,minutes:12},{id:'review',title:'Review vocabulary',description:'Due items · adaptive review',minutes:5},{id:'practice',title:'Practise Lexical Resource',description:'Precision · improve and retry',minutes:8},{id:'writing',title:'Apply in Writing',description:'Transfer new language to a paragraph',minutes:15}];let total=0,vocabulary=0;return tasks.filter(t=>{const isVocab=['learn','review'].includes(t.id);if(total+t.minutes>minutes||isVocab&&vocabulary+t.minutes>15)return false;total+=t.minutes;if(isVocab)vocabulary+=t.minutes;return true;});}
export function checkAnswer(answer,{type='free',item=null,drill=null,target=null}={}){
 const a=normal(answer),issues=[];const exact=normal(target||item?.phrase||drill?.answer||'');
 if(['meaning','recognition','collocation','choice'].includes(type)||type==='recall'){let ok=a===exact; if(type==='recall'&&!ok){const variants=exact.startsWith('place ')?[exact.replace('place ','places '),exact.replace('place ','placed ')]:exact.startsWith('allocate ')?[exact.replace('allocate ','allocates '),exact.replace('allocate ','allocated ')]:[];ok=variants.includes(a);}return{ok,issues:ok?[]:[type==='recall'?'Recall the complete phrase, including its preposition.':drill?.issue||'Look again at the meaning and the verb–noun combination.'],message:ok?'Correct. You retrieved the right expression.':'Not quite yet. Try the pattern again.',dimensions:null};}
 if(a.split(' ').filter(Boolean).length<6)issues.push('Write a complete sentence with a clear subject and verb.');
 if(/allocate(?:s|d)? for/.test(a))issues.push('“Allocate” needs an object: allocate funding or resources to a purpose.');
 if(/emphasis (to|for)|do emphasis|make emphasis/.test(a))issues.push('Use “place emphasis on” followed by a noun or an -ing form.');
 if(/juvenile individuals|copious quantities|aforementioned|utilisation of multitudinous/.test(a))issues.push('This sounds unnecessarily formal. Choose clear, ordinary academic language.');
 if(/\b(stuff|kids|a lot of things|very bad|something big)\b/.test(a))issues.push('Replace the informal or vague wording with a more precise description.');
 if(/\b(he|she|it) (have|are)\b|\b(they|we|people) (is|has)\b/.test(a))issues.push('Check subject–verb agreement.');
 if(item){const phrase=normal(item.phrase);const variants=[phrase,phrase.replace(/^place /,'places '),phrase.replace(/^place /,'placed '),phrase.replace(/^allocate /,'allocated '),phrase.replace(/^allocate /,'allocates ')];if(!variants.some(p=>a.includes(p)))issues.push(`Include the complete target expression “${item.phrase}” in your sentence.`);if(a===normal(item.example)&&type==='free')issues.push('Create a new context instead of copying the example.');}
 if(drill){const key=drill.key;if(key==='Repetition Control'&&!drill.newContext){if((a.match(/important/g)||[]).length>1)issues.push('“Important” still repeats. Combine the two benefits into a simpler structure.');if(!/economic/.test(a)||!/work|employ|job/.test(a))issues.push('Keep both original ideas: the economy and employment.');}else if(key==='Lexical Flexibility'&&!drill.newContext){if(!/government/.test(a)||!/public transport/.test(a)||!/more|greater|increase|additional/.test(a))issues.push(drill.issue);if(a===normal(drill.source))issues.push('Change the phrasing while preserving the meaning.');}else if(drill.keywords&&!drill.keywords.some(k=>a.includes(k)))issues.push(drill.issue);}
 const ok=issues.length===0;return{ok,issues,message:ok?'The local checks found a plausible use. Review the meaning and naturalness yourself, too.':'You have a useful starting point. Focus on the point below and retry.',dimensions:{Meaning:'Self-check',Collocation:issues.some(i=>/expression|Allocate|emphasis/.test(i))?'Review':'Pattern checked',Grammar:'Limited checks',Naturalness:'Self-check',Register:issues.some(i=>/formal|informal/.test(i))?'Review':'Basic checks',Appropriacy:'Self-check'}};
}
export function applyTransfer(s,text,now=Date.now()){const used=bank.filter(x=>s.items[x.id]&&normal(text).includes(normal(x.phrase)));for(const x of used)recordItem(s,x.id,'transfer',true,{now});return used;}
