const keyNotes={
  'Matching headings':'paragrafning asosiy g‘oyasi, uni dalillovchi gap va bitta chalg‘ituvchi sarlavha sababi',
  'Gap filling':'so‘z chegarasi, kerakli so‘z turkumi va matndagi dalil',
  'True / False / Not Given':'True/False uchun dalil va Not Given uchun yetishmayotgan ma’lumot',
  'Multiple choice':'to‘g‘ri variant dalili va noto‘g‘ri variantlar nima uchun chalg‘itishi',
};
export function guideStudyTask(task,skill,minutes){
  if(skill==='Speaking')return task;
  const t={...task};const topic=t.title.split(': ').slice(1).join(': ');const quantity=minutes<30?'2–3':'4–6';
  t.ifStuck=`Avval tushunmagan joyni belgilang va qayta urinib ko‘ring. Darsning kerakli qismini yoki mashq namunasini qayta oching. Hali ham tushunarsiz bo‘lsa, ustozingizga savolni shunday tayyorlang: “Resurs/mavzu: ${t.source}. Video vaqti yoki savol raqami: __. Men __ deb o‘yladim, chunki __. Namunadagi javob __. Aynan __ qismini tushuntirib bera olasizmi?” Ustozga murojaat qilish imkoni bo‘lmasa, savolni saqlab, osonroq namunani ishlab ko‘ring.`;
  t.reviewNext='Keyingi o‘qish kunining boshida shu xatoni javobga qaramasdan yana yeching. Bir necha kun o‘tib, yangi savolda ham shu usulni sinang.';
  t.checkpoint='Tekshirilgan javobning sababini o‘z so‘zingiz bilan tushuntira oling. Xato qolsa, ko‘proq yangi savolga o‘tishdan oldin o‘sha turdan kichik mashqni qayta bajaring.';
  if(t.resource==='readingVideo'){
    const exercise=['Matching headings','Gap filling'].includes(topic);
    const practice=exercise?`Reading mashqlari → ${topic}`:'CDI mock testlar → Reading';
    t.title=`Reading: ${topic} — dars va mashq`;
    t.source+=` + ${practice}`;
    t.description='Bir usulni o‘rganing, qisqa qayd oling va shu mashg‘ulotning o‘zida Ton Academy topshiriqlarida qo‘llang.';
    t.texts=[
      `Tegishli video qismini ko‘ring. Ko‘rish davomida ${keyNotes[topic]||'savol talabi, yechish qadamlari va chalg‘ituvchi javob sababi'}ni qisqa yozib boring; butun darsni ko‘chirmang.`,
      'Videoni yoping. Usulni xotiradan 2–3 qadam bilan yozing. Bitta namunada ustoz yechimini ko‘rishdan oldin o‘zingiz urinib ko‘ring.',
      `${practice} bo‘limini oching. Shu turdagi ${quantity} savolni mustaqil yeching; javob kalitini hozircha ochmang. ${exercise?'Har tanlov uchun sabab belgilang.':'Mos savol turini topmasangiz, videodagi namunani qayta ishlang va shu turdagi testni keyingi safar tanlang.'}`,
      'Javoblarni tekshiring. Xato savolda matndagi dalilni toping; “mening xato fikrim → to‘g‘ri dalil → keyingi usulim” shaklida qayd qiling.',
      'Eng qiyin savolni javobga qaramasdan qayta yeching. Hali tushunarsiz joy uchun video vaqti/savol raqami va aniq savolingizni yozing.'
    ];
    t.outcome='Natija: usul bo‘yicha qisqa qayd, tekshirilgan Ton mashqi va kamida bitta qayta ishlangan xato.';
  } else if(t.resource==='readingExercise'){
    t.texts=[
      `Avvalgi darsdagi usulni xotiradan yozing: ${keyNotes[topic]||'savol talabi va yechish qadamlari'}. Kerak bo‘lsa, faqat qiyin bo‘lgan video qismini qayta ko‘ring.`,
      `${quantity} ta yangi savolni javoblarga qaramasdan yeching. Har javobga matndan dalil belgilang; taxmin qilgan joyingizga “?” qo‘ying.`,
      'Javoblarni tekshiring. To‘g‘ri topilgan, lekin taxmin qilingan savollarni ham ko‘rib chiqing; chalg‘ituvchi variant yoki so‘z chegarasidagi xatoni aniqlang.',
      'Xato savollarni kalitni yopib qayta yeching. Shu usulni bitta yangi savolga ham qo‘llang.',
      'Qaydingizga savol raqami, xato sababi va to‘g‘ri usulni yozing. Tushunmagan joyingiz bo‘lsa, dalilingiz bilan aniq savol tayyorlang.'
    ];
  } else if(t.resource==='writingVideo'){
    t.source+=' + CDI mock testlar → Writing';
    t.texts=[
      'Darsning bitta usulni tushuntirgan qismini ko‘ring. Savol talabi, reja tuzilishi va ustoz aytgan asosiy xatoni qayd eting.',
      'Videoni to‘xtating. Namunadagi reja yoki gapni ustoz javobidan oldin o‘zingiz tuzing, keyin solishtiring.',
      `CDI Writing’dan shu task turiga mos savolni tanlang. ${topic==='Task 1'?'Asosiy tendensiyalarni topib, qisqa overview yozing.':'Savolga reja va bitta asosiy paragraf yozing; fikr, izoh va misolni bog‘lang.'} Bu ajratilgan vaqtda to‘liq test yozish vazifasi emas.`,
      'Yozganingizni darsdagi qoidalar bilan tekshiring. Savolga javob beryaptimi, fikr rivojlanganmi, parafraz ma’noni saqlaganmi? Bitta til xatosini ham tuzating.',
      'Eng zaif gap yoki qismini qayta yozing. Qaysi qoida yordam bergani va tushunarsiz qolgan joyni qaydingizga yozing.'
    ];
    t.outcome='Natija: Writing konspekti, CDI savolidan o‘zingiz yozgan qism va uning tuzatilgan varianti.';
  } else if(t.resource==='grammarVideo'){
    t.texts=[
      'Oldingi yozma ishingizdagi bitta takroriy xatoni tanlang. Ton Grammar’dan unga mos video qismini ko‘ring; qoida va bir to‘g‘ri namunani yozing.',
      'Videoni yoping va qoidani o‘z so‘zingiz bilan tushuntiring. Namunani ko‘chirmasdan, o‘zingizga tegishli gap tuzing.',
      `Writing mashqlari → Grammar bo‘limidan mos mashqni tanlab ${quantity} savolni bajaring. So‘ng shu tuzilma bilan 2 ta yangi gap yozing.`,
      'Namuna bilan tekshiring. Oldingi Writing ishingizdagi ayni xatoni ham tuzating; eski va yangi gapni yonma-yon yozing.',
      'Qoidaga qaramasdan bitta yangi gap tuzing. Ishlamagan joyingizni aniq savol sifatida qayd eting.'
    ];t.source+=' + Writing mashqlari → Grammar';
  } else if(t.resource==='writingExercise'){
    t.texts=[
      'Oldingi mashqdagi bitta xatoni xotiradan tuzating. Bugungi mashq ko‘rsatmasi va qisqa namunasini o‘qing.',
      ...(topic==='Paraphrasing'?[
        `${quantity} gapni asl ma’nosini saqlab qayta yozing. So‘z tanlovi bilan birga gap tuzilishini ham o‘zgartiring; ma’noni o‘zgartiradigan sinonimni majburan ishlatmang.`,
        'Asl va yangi gapni solishtiring: kim/nima, vaqt, miqdor va fikr kuchi o‘zgarmaganmi? Grammatika va tabiiy so‘z birikmalarini tekshiring.',
        'Zaif parafrazni qayta yozing, keyin bitta yangi gapda usulni mustaqil qo‘llang.'
      ]:topic==='Lexical resource'?[
        'Mashqdan 3–5 ta foydali so‘z birikmasini tanlang. Ma’nosi, qaysi so‘zlar bilan ishlatilishi va bitta tabiiy namunani yozing.',
        'Har bir birikma bilan o‘zingizga tegishli gap yozing. Namuna bilan solishtirib, noo‘rin ma’no yoki grammatik tuzilishni tuzating.',
        'Qaydlarni yoping. Birikmalarni xotiradan eslab, yangi gap yoki qisqa paragrafda ishlating; unutganlaringizni belgilang.'
      ]:[
        `${quantity} topshiriqni mustaqil bajaring. Javobdan tashqari, nega shu shakl yoki iborani tanlaganingizni ham ayting.`,
        'Qoida yoki namuna bilan tekshiring. Xato sababini aniqlab, eski va tuzatilgan gapni yonma-yon yozing.',
        'Qoidani o‘qib turmasdan shu tuzilma bilan yangi gap yozing va uni tekshiring.'
      ]),
      'Qaydingizga foydali qoida, tuzatilgan xato va bitta savolni yozing. Keyingi o‘qish kunida qiyin bo‘lganini xotiradan qayta bajaring.'
    ];
  } else if(t.resource==='listeningVideo'){
    t.source+=' + CDI mock testlar → Listening';
    t.texts=[
      `Videoda ${topic} savollarini yechish qismini ko‘ring. Savoldan oldin nimani tekshirish, qaysi signal so‘zlarni tinglash va xato javobdan qanday saqlanishni qayd eting.`,
      'Videoni namunada to‘xtating. Avval o‘zingiz javob toping, so‘ng ustoz izohi bilan solishtiring.',
      'CDI Listening’dan qisqa savollar to‘plamini tanlang. Savollarni oldindan o‘qib, kerakli so‘z turkumini belgilang; audioni tinglab mustaqil bajaring.',
      'Javoblarni tekshiring va xato joyni qayta tinglang. Muammo eshitish, ma’no, imlo yoki chalg‘ituvchi javobdami, yozing.',
      'Qiyin bo‘lgan qisqa audio bo‘lagini yana tinglab javobni tuzating. Tushunarsiz joyning vaqt belgisi bilan savol tayyorlang.'
    ];t.outcome='Natija: Listening usuli qaydlari, tekshirilgan CDI savollari va xato sabablari.';
  } else if(!t.steps){
    // CDI practice and review: preserve the task-specific action, add active retry and an error record.
    t.texts=[t.texts[0],t.texts[1],t.texts[2],
      skill==='Writing'?'Eng muhim xatoni tanlab, o‘sha gap yoki paragrafni qayta yozing. Yangi variant savolga aniqroq javob berishini tekshiring.':skill==='Reading'?'Kalitni yoping va xato savolni qayta yeching. Javobning matndagi dalilini o‘z so‘zingiz bilan tushuntiring.':'Xato joyni yana tinglang. Eshitilgan qisqa iborani yozib, asl javob bilan ma’no va imlo bo‘yicha tekshiring.',
      'Test nomi, savol raqami, xato sababi va keyingi safar ishlatadigan usulni yozing. Tushunarsiz joyni aniq savolga aylantiring.'
    ];
  }
  return t;
}
