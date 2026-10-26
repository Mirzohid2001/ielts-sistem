// Same-origin session API. Deliberately never reads or writes localStorage.
export function createAccountStore({endpoint='/ielts/vocabulary/api/',fetchImpl=globalThis.fetch,
  origin=globalThis.location?.origin,csrfToken=()=>{const meta=document.querySelector('meta[name="csrf-token"]')?.content;if(meta)return meta;const m=document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);return m?decodeURIComponent(m[1]):'';}}={}) {
  if(new URL(endpoint,origin).origin!==origin)throw new Error('Vocabulary Lab API must use the cabinet origin.');
  let revision=0,accountKey=null,latest=null,running=null,error=null,listener=()=>{};
  const state=()=>({pending:!!latest||!!running,error,revision});
  const emit=()=>listener(state());
  async function request(method,body) {
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
    try {
      const headers={Accept:'application/json'};
      if(body){headers['Content-Type']='application/json';headers['X-CSRFToken']=csrfToken();}
      const response=await fetchImpl(endpoint,{method,headers,credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal,...(body?{body:JSON.stringify(body)}:{})});
      const data=await response.json().catch(()=>null);
      if(!response.ok){const e=new Error(data?.error||`HTTP_${response.status}`);e.status=response.status;e.code=data?.error;throw e;}
      if(!data||!Number.isSafeInteger(data.revision)||data.revision<0)throw new Error('INVALID_API_RESPONSE');
      return data;
    } finally {clearTimeout(timer);}
  }
  async function pump() {
    if(running||error||!latest)return running;
    running=(async()=>{
      while(latest&&!error){
        const snapshot=latest;latest=null;
        try {
          const result=await request('PUT',{accountKey,baseRevision:revision,document:snapshot});
          if(result.accountKey!==accountKey||result.revision!==revision+1)throw new Error('INVALID_API_RESPONSE');
          revision=result.revision;
        } catch(e){latest=latest||snapshot;error=e;}
      }
    })();
    emit();await running;running=null;emit();
    if(latest&&!error)return pump();
  }
  return {
    async load(){const data=await request('GET');if(typeof data.accountKey!=='string'||!data.accountKey||!('document' in data))throw new Error('INVALID_API_RESPONSE');revision=data.revision;accountKey=data.accountKey;return data.document;},
    subscribe(fn){listener=fn;emit();},
    save(doc){if(!accountKey)throw new Error('LOAD_REQUIRED');latest=structuredClone(doc);emit();void pump();},
    retry(){if(error&&[401,403,409].includes(error.status))return false;error=null;emit();void pump();return true;},
    state,
    async settled(){while(running)await running;return state();}
  };
}
