import {SPEAKING_RESOURCES,speakingLesson} from './speaking.js';
import {guideStudyTask} from './study-method.js';
import {t} from './i18n.js';
export const CONTENT_VERSION = 3;
const member = (nameKey,shortKey) => ({get name(){return t(nameKey);},get short(){return t(shortKey);},url:'https://tonielts.uz/',get access(){return t('resNeedAccount');}});
export const RESOURCE = {
  ...SPEAKING_RESOURCES,
  readingVideo:member('resReadingVideo','resReadingVideoShort'),
  writingVideo:member('resWritingVideo','resWritingVideoShort'),
  listeningVideo:member('resListeningVideo','resListeningVideoShort'),
  grammarVideo:member('resGrammarVideo','resGrammarVideoShort'),
  readingExercise:member('resReadingEx','resReadingExShort'),
  writingExercise:member('resWritingEx','resWritingExShort'),
  cdiReading:{get name(){return t('resCdiReading');},short:'CDI Reading',url:'https://tonielts.uz/',get access(){return t('resNeedAccount');}},
  cdiListening:{get name(){return t('resCdiListening');},short:'CDI Listening',url:'https://tonielts.uz/',get access(){return t('resNeedAccount');}},
  cdiWriting:{get name(){return t('resCdiWriting');},short:'CDI Writing',url:'https://tonielts.uz/',get access(){return t('resNeedAccount');}},
  // Retained only so completed tasks from the original release remain readable.
  video:{get name(){return t('resVideoLegacy');},url:'https://tonacademy.uz/videos/',get access(){return t('resFreeDemo');}},
  reading:{get name(){return t('resReadingLegacy');},url:'https://tonacademy.uz/courses/',get access(){return t('resFreeDemo');}},
  listening:{get name(){return t('resListeningLegacy');},url:'https://tonacademy.uz/courses/',get access(){return t('resFreeDemo');}},
  platform:member('resPlatform','resPlatformShort'),
  writing:{get name(){return t('resWritingAi');},short:'AI Writing Checker',url:'https://tonielts.uz/',get access(){return t('resNeedAccount');}},
  live:member('resLive','resLiveShort'),
};
const READING_TOPICS = [
  ['Matching headings','har paragrafning asosiy g‘oyasini topish','Sarlavhani moslang va tanlovingizni paragrafning asosiy g‘oyasi bilan asoslang.'],
  ['Gap filling','so‘z chegarasi va grammatik moslik','Bo‘sh joylarni to‘ldiring. So‘z chegarasi, imlo va gap grammatikasini tekshiring.'],
  ['True / False / Not Given','matndagi dalil va ma’lumot yo‘qligini farqlash','Har javob uchun matndagi dalilni toping. Not Given javobida qaysi ma’lumot yetishmasligini yozing.'],
  ['Matching information','kerakli ma’lumotni paragrafdan topish','Savolni parafraz qiling va shu ma’lumot berilgan paragrafni belgilang.'],
  ['Multiple choice','to‘g‘ri javob va chalg‘ituvchi variantlar','Javobni tanlang. Har noto‘g‘ri variant nima uchun mos kelmasligini tekshiring.'],
  ['Summary completion','qisqa mazmundagi bo‘sh joylar','Matn mazmuniga mos javob toping. So‘z turkumi va belgilangan so‘z chegarasini tekshiring.'],
  ['Matching sentence endings','gap boshi va oxirining mazmuniy mosligi','Gap qismlarini moslang va to‘liq gapning matndagi dalilini belgilang.'],
  ['Matching features','fikrlarni odam, guruh yoki xususiyatga moslash','Har javobni matndagi tegishli shaxs yoki xususiyat bilan tekshiring.'],
  ['Diagram labelling','tasvir va matndagi ma’lumotni bog‘lash','Tasvirdagi bo‘sh joylarni matn asosida to‘ldiring. Joylashuv va imloni tekshiring.'],
];
const LISTENING_TOPICS = [
  ['Gap filling','so‘z chegarasi, raqamlar va imlo'],
  ['Multiple choice','chalg‘ituvchi javoblarni ajratish'],
  ['Map / plan labelling','yo‘nalish va joylashuv ifodalari'],
  ['Matching','variantlarni eshitilgan ma’lumotga moslash'],
  ['Note / table completion','asosiy ma’lumotlarni tartib bilan yozish'],
];
function steps(minutes,texts){
  const weights=texts.length===5?[.25,.10,.35,.20,.10]:texts.map(()=>1/texts.length);
  const allocation=texts.map(()=>2);
  const remaining=minutes-2*texts.length;
  const total=weights.reduce((a,b)=>a+b,0);
  weights.forEach((w,i)=>allocation[i]+=Math.floor(remaining*w/total));
  for(let i=0;allocation.reduce((a,b)=>a+b,0)<minutes;i++)allocation[i%texts.length]++;
  return texts.map((text,i)=>({minutes:allocation[i],text}));
}
function activity(resource,title,source,description,texts,outcome){return {resource,title,source,description,texts,outcome};}
function readingVideo(topic){return activity('readingVideo',`Reading video: ${topic[0]}`,`Video darslar → Reading → ${topic[0]}`,'Ton Academy’dagi shu savol turini tushuntiradigan yozib olingan darsni oching.',[
  `Darsning ${topic[1]} haqidagi qismini ko‘ring. Tugamasa, davom etish joyini belgilab qo‘ying.`,
  'Videoni namunaviy savolda to‘xtating. Ustoz javobini ko‘rishdan oldin o‘zingiz yechib, keyin usulingizni solishtiring.',
  'Amaliyotda ishlatadigan 3 qadam va yo‘l qo‘ymaslik kerak bo‘lgan bitta xatoni yozing.'
],'Natija: yechish usuli bo‘yicha qisqa konspekt va ishlangan namuna.');}
function readingExercise(topic){return activity('readingExercise',`Reading mashqi: ${topic[0]}`,`Reading mashqlari → ${topic[0]}`,'Ton Academy Reading mashqlari bo‘limida shu turdagi bajarilmagan mashqni oching.',[
  'Video darsdagi usulni eslang. Mashq ko‘rsatmasi va savollarni o‘qing.',
  topic[2]+' Ajratilgan vaqtga sig‘adigan savollarni mustaqil bajaring.',
  'Javoblarni tekshiring. Xato javoblarni tuzating va har biri uchun sabab yozing.'
],'Natija: bajarilgan mashq, to‘g‘ri javoblar soni va xatolar ro‘yxati.');}
function readingCDI(topic){return activity('cdiReading',`CDI Reading: ${topic?topic[0]:'bitta passage'}`,`CDI mock testlar → Reading`,'Ton Academy CDI Reading testidan bitta passage yoki kerakli savollar to‘plamini tanlang.',[
  'CDI testni oching. Ishlamoqchi bo‘lgan passage yoki savollarni tanlang; bu mashg‘ulot to‘liq mock test emas.',
  topic?topic[2]+' Shu turdagi savollarni topmasangiz, bitta passage savollarini bajaring.':'Savollarni vaqtingizni kuzatib yeching. Bir savolda uzoq qolib ketmang.',
  'Javoblarni tekshiring, xatoning matndagi dalilini toping va test nomini qayd eting.'
],'Natija: CDI testdagi ishlangan qism va keyingi mashq uchun xato turlari.');}
function writingVideo(topic,focus){return activity('writingVideo',`Writing video: ${topic}`,`Video darslar → Writing → ${topic}`,'Ton Academy’dagi tegishli Writing video darsini oching.',[
  `Darsning ${focus} haqidagi qismini ko‘ring va tugamagan joyini belgilang.`,
  'Ustoz ko‘rsatgan namunani avval mustaqil ishlab ko‘ring. Keyin video tushuntirishi bilan solishtiring.',
  'Keyingi Writing mashqida qo‘llaydigan 3 qoidani yozib oling.'
],'Natija: Writing usuli bo‘yicha konspekt va o‘zingiz ishlagan namuna.');}
function writingExercise(type){
  const data={
    Paraphrasing:['asl ma’noni saqlab, so‘z va gap tuzilishini o‘zgartirish','Berilgan gaplarni ma’nosini o‘zgartirmasdan qayta yozing. Faqat sinonim almashtirish bilan cheklanmang.','Natija: parafraz qilingan gaplar va tuzatilgan xatolar.'],
    'Lexical resource':['so‘z birikmalarini kontekstda o‘rganish','Mashqdagi so‘z va collocationlarni o‘rganing. Har biri bilan o‘zingizga tegishli yangi gap yozing.','Natija: kontekstli lug‘at qaydlari va yangi gaplar.'],
    Grammar:['grammatik aniqlikni oshirish','Writing bo‘limidagi grammatika mashqini bajaring. Shu tuzilmani o‘zingiz yozgan gaplarda ham qo‘llang.','Natija: tekshirilgan grammatika mashqi va to‘g‘ri tuzilgan gaplar.'],
  }[type];
  return activity('writingExercise',`Writing mashqi: ${type}`,`Writing mashqlari → ${type}`,`Ton Academy Writing mashqlaridan ${type} mashqini tanlang. Maqsad — ${data[0]}.`,[
    'Mashqdagi qoida va namunalarni o‘qing. Oldin ishlamagan topshiriqni tanlang.',data[1],
    'Mashq ko‘rsatmasi yoki namunasi bilan tekshiring. Qiyin bo‘lgan gaplarni qayta yozing.'
  ],data[2]);
}
function grammarVideo(){return activity('grammarVideo','Grammar video: qoidani amalda qo‘llang','Video darslar → Grammar','Ton Academy Grammar darslaridan oxirgi yozma ishingizda qiynalgan mavzuni tanlang.',[
  'Qoidani tushuntiradigan video qismini ko‘ring. Namunalardagi gap tuzilishiga e’tibor bering.',
  'Videoni to‘xtatib, namunaga o‘xshash o‘z gaplaringizni yozing. Oldingi ishingizdagi shu turdagi xatoni tuzating.',
  'Qoida, bitta to‘g‘ri namuna va oldingi xatongizni yonma-yon yozing.'
],'Natija: Grammar konspekti va tuzatilgan Writing gaplari.');}
function writingCDI(){return activity('cdiWriting','CDI Writing: reja va bitta paragraf','CDI mock testlar → Writing','Ton Academy CDI Writing testidan bitta Task 2 savolini oching. Bu to‘liq test emas, yozish amaliyoti.',[
  'Savolning barcha qismlarini ajrating. Pozitsiyangiz va ikkita asosiy fikrdan reja tuzing.',
  'Bitta asosiy paragraf yozing: fikr, izoh va misol. Ton Writing darsidagi usulni qo‘llang.',
  'Paragraf savolga javob berishini, parafraz, lug‘at va grammatikasini tekshiring.'
],'Natija: CDI savoliga reja va tekshirilgan asosiy paragraf.');}
function listeningVideo(topic){return activity('listeningVideo',`Listening video: ${topic[0]}`,`Video darslar → Listening → ${topic[0]}`,'Ton Academy’dagi tegishli Listening video darsini oching.',[
  `Darsda ${topic[1]} bo‘yicha tushuntirishni ko‘ring.`,
  'Namunaviy topshiriqni ustoz javobidan oldin bajarib ko‘ring. Keyin yechish usulingizni solishtiring.',
  'CDI Listening amaliyotida ishlatadigan 3 tavsiyani yozing.'
],'Natija: savol turiga mos usul va ishlangan video namuna.');}
function listeningCDI(){return activity('cdiListening','CDI Listening: bitta bo‘lim','CDI mock testlar → Listening','Ton Academy CDI Listening testidan ajratilgan vaqtingizga mos bitta bo‘limni tanlang.',[
  'Savollarni oldindan o‘qing. Kerakli so‘z turkumi va kalit so‘zlarni belgilang.',
  'Tanlangan bo‘lim audiosini tinglab, javoblarni kiriting. Imlo va so‘z chegarasiga amal qiling.',
  'Javoblarni tekshiring. Xato chiqqan qismlarni qayta tinglab, sababini qayd eting.'
],'Natija: CDI Listening bo‘limi, to‘g‘ri javoblar soni va xato sabablari.');}
function review(skill){

  if(skill==='Writing')return activity('writingExercise','Writing: oldingi xatolarni tuzating','Writing mashqlari → Paraphrasing / Lexical resource / Grammar','Oldingi CDI Writing ishingiz yoki Writing mashqingizdagi takroriy xatoni tanlang.',[
    'Muammoni ajrating: parafraz, so‘z tanlash yoki grammatika. Mos Ton Writing mashqini oching.',
    'Mos mashqni bajaring, keyin oldingi yozma ishingizdagi shu xatolarni tuzating.',
    'Eski va yangi gapni solishtiring. Qayta yo‘l qo‘ymaslik uchun qisqa qoida yozing.'
  ],'Natija: takrorlangan Writing mashqi va yaxshilangan yozma ish.');
  return activity(skill==='Reading'?'cdiReading':'cdiListening',`CDI ${skill}: xatolar tahlili`,`CDI mock testlar → ${skill}`,`Oldingi Ton CDI ${skill} testingizni oching. Hali test ishlamagan bo‘lsangiz, kichik bir qismini bajaring.`,[
    'Noto‘g‘ri javoblarni ko‘rib, qiyin bo‘lgan savollarni tanlang.',
    skill==='Reading'?'Savollarni qayta yeching. Har bir javobning matndagi dalili va parafrazini belgilang.':'Xato chiqqan audio qismlarini qayta tinglang. Eshitish, imlo va chalg‘ituvchi javob xatolarini ajrating.',
    'Xato sababi va keyingi safar ishlatadigan usulni yozing.'
  ],'Natija: tuzatilgan javoblar va takrorlash kerak bo‘lgan savol turlari.');
}
function fullMock(skill,minutes){
  const reading=skill==='Reading',writing=skill==='Writing';
  const task=activity(reading?'cdiReading':writing?'cdiWriting':'cdiListening',`CDI ${skill}: to‘liq mock test`,`CDI mock testlar → ${skill}`,'Ton Academy CDI bo‘limida hali ishlamagan testingizni tanlang va test sharoitida bajaring.',[],`Natija: tugallangan CDI ${skill} testi va saqlangan ish/natija.`);
  task.minimumDuration=60;
  task.steps=writing?[{minutes:20,text:'CDI Writing Task 1 ni bajaring. Asosiy ma’lumotlar va taqqoslashlarni yoritishga e’tibor bering.'},{minutes:40,text:'CDI Writing Task 2 ni yozing. Rejalash va yakuniy tekshiruvni shu vaqt ichiga kiriting; ishingizni saqlang.'}]:reading?[{minutes:60,text:'CDI Reading testini 60 daqiqada, tashqi yordamsiz bajaring. Javoblarni shu vaqt ichida tekshirib, natijani saqlang.'}]:[{minutes:40,text:'CDI Listening testini audioga amal qilib, pauzasiz bajaring; test taymeriga rioya qiling. Erta tugatsangiz, qolgan vaqtda javoblarni tekshiring.'},{minutes:20,text:'Natijani saqlang. Xato chiqqan joylarni qayta tinglab, imlo va tushunish xatolarini yozing.'}];
  if(minutes>60)task.steps.push({minutes:minutes-60,text:'Natijani ko‘rib chiqing va keyingi mashg‘ulot uchun qiyin savollarni belgilang.'});
  return task;
}
export function makeLesson(skill,index,phase,minutes){
  let task;
  if(skill==='Speaking')task=speakingLesson(index,phase,minutes);
  else if(phase.key==='review')task=review(skill);
  else if(phase.key==='mock') {
    if(index%2===1)task=review(skill);
    else if(minutes>=60&&skill!=='Speaking')task=fullMock(skill,minutes);
    else task=skill==='Reading'?readingCDI():skill==='Listening'?listeningCDI():writingCDI();
  } else if(skill==='Reading') {
    const topic=READING_TOPICS[Math.floor(index/3)%READING_TOPICS.length];
    task=index%3===0?readingVideo(topic):index%3===1?(Math.floor(index/3)%READING_TOPICS.length<2?readingExercise(topic):readingCDI(topic)):readingCDI(topic);
  } else if(skill==='Listening') {
    const topic=LISTENING_TOPICS[Math.floor(index/3)%LISTENING_TOPICS.length];
    task=index%3===0?listeningVideo(topic):index%3===1?listeningCDI():review('Listening');
  } else if(skill==='Writing') {
    const writingCycle=[()=>writingVideo('Task 2','savol turini tahlil qilish va reja tuzish'),()=>writingExercise('Paraphrasing'),()=>writingExercise('Lexical resource'),grammarVideo,()=>writingExercise('Grammar'),writingCDI,()=>writingVideo('Task 1','ma’lumotlarni tanlash va overview yozish'),()=>writingExercise('Paraphrasing'),writingCDI,()=>review('Writing')];
    task=writingCycle[index%writingCycle.length]();
  }
  task=guideStudyTask(task,skill,minutes);
  const result={...task,minimumDuration:task.minimumDuration||15,steps:task.steps||steps(minutes,task.texts),lessonIndex:index,phaseKey:phase.key,contentVersion:CONTENT_VERSION};
  delete result.texts;return result;
}
