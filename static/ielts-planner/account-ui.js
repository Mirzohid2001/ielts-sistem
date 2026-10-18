export function showLoadFailure(){
  document.body.inert=false;
  const root=document.getElementById('planner-app')||document.body;
  const main=document.createElement('div');main.className='account-message';
  main.innerHTML='<h1>Reja yuklanmadi.</h1><p>Hisobingizga kirganingizni va internetni tekshiring. Saqlangan reja yuklanmaguncha yangi reja yozilmaydi.</p><button class="primary-button" type="button">Qayta yuklash</button>';
  main.querySelector('button').onclick=()=>location.reload();root.replaceChildren(main);
}
export function showSaveRecovery(store,documentSnapshot){
  const modal=document.createElement('dialog');modal.className='account-recovery';
  modal.innerHTML='<h2>O‘zgarishlar hali saqlanmadi</h2><p>Avval JSON nusxasini yuklab oling. Boshqa oynada reja o‘zgargan yoki hisob almashgan bo‘lsa, sahifani qayta yuklang. Nusxani IT jamoasi yordamida tekshirib tiklash mumkin.</p><div class="account-actions"><button data-action="download" class="primary-button">JSON nusxa</button><button data-action="retry" class="secondary-button">Qayta saqlash</button><button data-action="reload" class="secondary-button">Sahifani yangilash</button><button data-action="close" class="secondary-button">Yopish</button></div><p class="hint" data-message></p>';
  modal.addEventListener('click',e=>{
    const action=e.target.dataset.action;
    if(action==='close'){modal.close();modal.remove();}
    if(action==='reload')location.reload();
    if(action==='retry'){
      if(store.retry()){modal.close();modal.remove();}
      else modal.querySelector('[data-message]').textContent='Hisob, ruxsat yoki reja versiyasi o‘zgargan. JSON nusxani oling va sahifani yangilang.';
    }
    if(action==='download'){
      const url=URL.createObjectURL(new Blob([JSON.stringify(documentSnapshot,null,2)],{type:'application/json'}));
      const a=document.createElement('a');a.href=url;a.download='ton-ielts-unsaved-plan.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
  });
  document.body.append(modal);modal.showModal();
  modal.addEventListener('close',()=>modal.remove(),{once:true});
}
