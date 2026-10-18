import {t} from './i18n.js';
export const SPEAKING_RESOURCES = {
  speakingShadowing:{get name(){return t('resSpeakShadow');},get short(){return t('resSpeakShadowShort');},url:'https://learnenglish.britishcouncil.org/free-resources/speaking',get access(){return t('resSpeakShadowAccess');},get linkLabel(){return t('resSpeakShadowLink');},selfStudy:true},
  speakingQuestions:{get name(){return t('resSpeakQ');},get short(){return t('resSpeakQShort');},url:'https://takeielts.britishcouncil.org/prepare/ielts-free-practice-mock-tests/academic/speaking',get access(){return t('resSpeakQAccess');},get linkLabel(){return t('resSpeakQLink');},selfStudy:true},
  speakingRecording:{get name(){return t('resSpeakRec');},get short(){return t('resSpeakRecShort');},url:null,get access(){return t('resSpeakRecAccess');},selfStudy:true},
};
const help='Tushunarsiz talaffuz yoki iborani yozuv vaqti bilan belgilang. Qisqa bo‘lakni qayta tinglang, matn bilan tekshiring va sekin takrorlang. Hali ham qiyin bo‘lsa, qisqaroq yoki osonroq material oling; yordam so‘rasangiz, aynan o‘sha bo‘lak va o‘z urinishlaringizni ko‘rsating.';
function task(resource,title,description,texts,outcome,checkpoint){return {resource,title,source:resource==='speakingRecording'?'Mustaqil Speaking → diktofon va oldingi yozuvlar':resource==='speakingShadowing'?'Mustaqil Speaking → British Council video + diktofon':'Mustaqil Speaking → rasmiy namuna savollari + diktofon',description,texts,outcome,checkpoint,ifStuck:help,reviewNext:'Keyingi Speaking mashg‘ulotida shu xatoni yana tekshiring va yangi savolda tuzatilgan usulni qo‘llang.'};}
function shadowing(){return task('speakingShadowing','Speaking: shadowing → o‘z so‘zingiz bilan aytish','Ma’nosini asosan tushunadigan, matni berilgan videodan 20–40 soniyalik parcha tanlang. Maqsad — tushunarli talaffuz, urg‘u va ritm.',[
  'Parchani avval tinglab, mazmunini tushuning. Keyin matnda urg‘uli so‘zlar, pauzalar va bir-biriga ulanadigan tovushlarni belgilang.',
  'Bitta qisqa gapni tinglang, pauza qiling va takrorlang. Qiyin bo‘lakni avval sekin, keyin tabiiy tezlikda ayting.',
  'Endi ovoz ortidan birga gapiring — shadowing qiling. Qisqa parchani 2–3 marta takrorlab, oxirgi urinishni diktofonga yozing.',
  'O‘z yozuvingizni namuna bilan solishtiring. Faqat 1–2 muammoni tanlang: urg‘u, pauza yoki tushunarsiz tovush. Shu qismlarni qayta yozing.',
  'Matnni yoping va mazmunni o‘z gaplaringiz bilan 30–60 soniyada ayting. Bitta foydali iborani boshqa, o‘zingizga tegishli gapda ishlating.'
],'Natija: namuna havolasi va vaqti, ikkita qisqa yozuv va bitta tuzatilgan talaffuz muammosi.','Faqat taqlid qilish bilan tugatmang: oxirida ma’noni matnsiz, tushunarli qilib ayta oldingizmi?');}
function part1(){return task('speakingQuestions','Speaking Part 1: javob → sabab → misol','Rasmiy namunalardan tanish mavzudagi 3–4 ta Part 1 savolini tanlang. To‘liq javobni oldindan yozmang yoki yodlamang.',[
  'Savollarni o‘qing. Har biriga faqat 2–3 ta kalit so‘z yozing; keraksiz murakkab iboralarni qidirmang.',
  'Savollarga tabiiy javob bering va diktofonga yozing. To‘g‘ridan-to‘g‘ri javobga qisqa sabab yoki shaxsiy misol qo‘shing.',
  'Yozuvni tinglang. Javobsiz qolgan savol, uzoq pauza yoki takrorlangan so‘zni belgilang. Eng qiyin javobning qisqa bo‘lagini yozib ko‘ring.',
  'Faqat ikkita muammoni tuzating va o‘sha savollarga qayta javob bering. Yozilgan matnni o‘qimang.',
  'Yangi bitta savolga tayyorgarliksiz javob bering. Yaxshilangan jihat va keyingi mashq maqsadini qayd eting.'
],'Natija: birinchi va ikkinchi urinishlar, ikki tuzatish va yangi savolga mustaqil javob.','Javob savolga mos, tushunarli va qisqa izoh bilan rivojlantirilganmi?');}
function part2(){return task('speakingQuestions','Speaking Part 2: 1 daqiqa reja, 2 daqiqa nutq','Rasmiy namunadan bitta Part 2 mavzusini tanlang. Telefonda taymer va diktofonni tayyorlang.',[
  'Mavzuning barcha bandlarini o‘qing. Ayta oladigan haqiqiy voqea yoki misolni tanlang; to‘liq matn yozmang.',
  'Taymer bilan 1 daqiqa reja qiling: kim/nima, qachon/qayerda, tafsilot va nima uchun muhim. Faqat kalit so‘zlarni yozing.',
  '2 daqiqagacha gapirib ovoz yozing. Fikr tugasa, aniq voqea, sabab yoki his-tuyg‘u bilan rivojlantiring. O‘rtada qaytadan boshlamang.',
  'Yozuvni tinglang. Qaysi band ochilmaganini va bitta ravonlik yoki grammatik muammoni toping. Kalit so‘zlaringizni tuzating.',
  'Matnsiz qayta gapiring. Ikki yozuvdagi mazmun va tushunarlilikni solishtiring; keyingi safar mashq qiladigan bir jihatni yozing.'
],'Natija: bir daqiqalik kalit so‘zlar rejasi, ikki nutq yozuvi va aniq rivojlantirish maqsadi.','Mavzuni ochdingizmi va misol bilan rivojlantirdingizmi? Tez gapirish emas, mazmun va tushunarlilikni tekshiring.');}
function part3(){return task('speakingQuestions','Speaking Part 3: fikrni chuqurlashtiring','Rasmiy namunalardan 2–3 ta “why / how / compare” mazmunidagi Part 3 savolini tanlang.',[
  'Savol aynan nimani so‘rayotganini aniqlang. Har savol uchun bir fikr, bir sabab va bir misoldan kalit so‘z yozing.',
  'Javoblarni diktofonga ayting. Fikr → sabab → misol tartibidan foydalaning; mos bo‘lsa, istisno yoki qarama-qarshi holatni ham ayting.',
  'Yozuvni tinglang: dalil fikrni tushuntiryaptimi yoki faqat takrorlayaptimi? Bitta sayoz izoh va bitta til xatosini toping.',
  'Sayoz izohni aniq sabab yoki misol bilan almashtiring. O‘sha javobni tabiiy ravishda qayta ayting.',
  'Yangi savolga shu usul bilan javob bering. Keyingi safar tekshirish uchun bitta ochiq savol yoki qiyinchilikni yozing.'
],'Natija: sabab va misolli javoblar, tuzatilgan bitta dalil va yangi savolga javob.','Javob savolga bevosita javob beradimi? Sabab va misol bir-biriga mantiqan bog‘langanmi?');}
function recordingReview(){return task('speakingRecording','Speaking: yozuvni tahlil qiling va qayta ayting','Oldingi Speaking yozuvingizni tanlang. Yozuv bo‘lmasa, o‘qish, ish yoki kundalik odatingiz haqida bir daqiqa gapirib yozing.',[
  'Yozuvni bir marta to‘liq tinglang. Asosiy fikr tushunarlimi va gaplar bir-biriga bog‘langanmi, belgilang.',
  'Qiyin bo‘lgan 20–30 soniyani aynan aytganingizdek yozing. Pauza, takroriy so‘z va tugallanmagan gaplarni belgilang.',
  'Eng muhim ikki muammoni tuzating: masalan, noaniq fikr va bitta grammatik xato. Javobni sun’iy murakkablashtirmang.',
  'Qaydlarni yoping va shu fikrni yana aytib yozing. Ikki urinishni tushunarlilik va ravonlik bo‘yicha solishtiring.',
  'Yaxshilangan jihatni va keyingi yangi mavzuda tekshiriladigan bitta maqsadni yozing. O‘zingizga taxminiy band qo‘yishga urinmang.'
],'Natija: qisqa transkript, ikkita tuzatish va oldin/keyin yozuvlari.','O‘sha xatolar kamayganmi? Yangi mavzuda ham matnsiz va tushunarli gapira olasizmi?');}
function speakingMock(minutes){const t=task('speakingQuestions','Speaking: Parts 1–3 ni mustaqil sinash','Rasmiy namuna savollari, taymer va diktofon bilan bir urinish qiling. Bu o‘zingiz mashq qiladigan simulyatsiya; jonli imtihondagi suhbatni to‘liq takrorlamaydi.',[],
  'Natija: uzluksiz sinov yozuvi, ikki ustuvor muammo va qayta ishlangan javob.','Ravonlik, lug‘at, grammatika va talaffuz bo‘yicha har biriga bitta kuzatuv yozing. Faqat ikkita muammoni keyingi mashqda tuzating.');
  t.minimumDuration=30;
  t.steps=[{minutes:2,text:'Namuna savollarini oching. Diktofonni yoqing; savollarni ekran yoki qog‘ozdan o‘qing, tayyor javoblarni o‘qimang.'},{minutes:14,text:'Part 1 uchun 4–5 daqiqa, Part 2 uchun 1 daqiqa reja va 2 daqiqagacha nutq, Part 3 uchun 4–5 daqiqa ajrating. Urinishni to‘xtatib tuzatmang.'},{minutes:minutes-22,text:'Yozuvni tinglang. Savolga moslik va tushunarlilikni tekshiring, keyin ikkita asosiy muammoni tanlang.'},{minutes:4,text:'Eng qiyin javobni sabab yoki misol bilan yaxshilang va qayta yozing.'},{minutes:2,text:'Xatolar ro‘yxatiga keyingi Speaking mashg‘uloti uchun bitta aniq maqsad yozing.'}];return t;}
export function speakingLesson(index,phase,minutes){
  if(phase.key==='review')return index%2?shadowing():recordingReview();
  if(phase.key==='mock'&&index%3===0&&minutes>=30)return speakingMock(minutes);
  return [shadowing,part1,part2,part3,recordingReview][index%5]();
}
