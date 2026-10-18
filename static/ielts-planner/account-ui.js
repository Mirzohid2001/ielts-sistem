import {t} from './i18n.js';

export function showLoadFailure(){
  document.body.inert=false;
  const root=document.getElementById('planner-app')||document.body;
  const main=document.createElement('div');main.className='account-message';
  main.innerHTML=`<h1>${t('loadFailTitle')}</h1><p>${t('loadFailBody')}</p><button class="primary-button" type="button">${t('reload')}</button>`;
  main.querySelector('button').onclick=()=>location.reload();root.replaceChildren(main);
}
export function showSaveRecovery(store,documentSnapshot){
  const modal=document.createElement('dialog');modal.className='account-recovery';
  modal.innerHTML=`<h2>${t('recoveryTitle')}</h2><p>${t('recoveryBody')}</p><div class="account-actions"><button data-action="download" class="primary-button">${t('jsonCopy')}</button><button data-action="retry" class="secondary-button">${t('retrySave')}</button><button data-action="reload" class="secondary-button">${t('refreshPage')}</button><button data-action="close" class="secondary-button">${t('close')}</button></div><p class="hint" data-message></p>`;
  modal.addEventListener('click',e=>{
    const action=e.target.dataset.action;
    if(action==='close'){modal.close();modal.remove();}
    if(action==='reload')location.reload();
    if(action==='retry'){
      if(store.retry()){modal.close();modal.remove();}
      else modal.querySelector('[data-message]').textContent=t('recoveryConflict');
    }
    if(action==='download'){
      const url=URL.createObjectURL(new Blob([JSON.stringify(documentSnapshot,null,2)],{type:'application/json'}));
      const a=document.createElement('a');a.href=url;a.download='ton-ielts-unsaved-plan.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
  });
  document.body.append(modal);modal.showModal();
  modal.addEventListener('close',()=>modal.remove(),{once:true});
}
