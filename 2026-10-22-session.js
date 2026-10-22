/* Explicit activation; bounded status checks; no installation inference from network failure. */
let startingStudio=false,heartbeatBusy=false,startAttempt=0;
function connectionPanel(message,error=false,waiting=false){
 const n=$('connection-notice');n.hidden=false;n.replaceChildren();n.classList.toggle('connection-warning',error);
 n.setAttribute('role',error?'alert':'status');const p=document.createElement('p');p.textContent=message;n.append(p);
 const actions=document.createElement('div');actions.className='connection-actions';
 const control=document.createElement('button');control.type='button';control.textContent=waiting?'시작 취소':'다시 시도';control.onclick=waiting?cancelStudioStart:()=>startStudio();actions.append(control);
 const a=document.createElement('a');a.className='secondary-button';a.href='./manual.html#install';a.target='_blank';a.rel='noopener';a.textContent='설치·복구 안내';const download=document.createElement('a');download.className='secondary-button';download.href='./downloads/2026-10-22-Local-Voice-Studio-Setup-v1.4.0.exe';download.download='';download.textContent='Windows 설치·복구 프로그램';actions.append(download);actions.append(a);n.append(actions);
 stage(message,error);
}
function showStartHelp(message){connectionPanel(message,true,false)}
function cancelStudioStart(){
 startAttempt++;startingStudio=false;if(busy&&!serverReady)disable(false);$('engine-connect').disabled=false;$('engine-connect').textContent='스튜디오 시작';
 connectionPanel('시작 요청을 취소했습니다. 이미 열린 로컬 승인 창도 닫아 주세요. 엔진이 켜졌더라도 연결 탭과 작업이 없으면 자동 종료합니다.');
}
async function sessionFetch(path,data,auth=''){
 const c=new AbortController(),timer=setTimeout(()=>c.abort(),3000);
 try{
  const response=await fetch(engineBase+path,{method:data===undefined?'GET':'POST',headers:{...(data===undefined?{}:{'Content-Type':'application/json'}),...(auth?{'X-App-Token':auth}:{})},body:data===undefined?undefined:JSON.stringify(data),targetAddressSpace:'loopback',signal:c.signal});
  const value=await response.json();if(!response.ok){const e=Error(value.error||'엔진 응답 오류');e.status=response.status;throw e}return value;
 }finally{clearTimeout(timer)}
}
async function startStudio(required=false){
 if(startingStudio)return;
 if(serverReady){stage('엔진 연결됨 · 마지막 탭이 닫히면 작업 완료 후 자동 종료합니다.');return}
 if(location.protocol==='file:'){showStartHelp('HTML 파일 대신 배포 웹 주소로 접속하세요.');return}
 const attempt=++startAttempt,started=Date.now(),deadline=started+45000;
 const nonce=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
 let pendingToken='',phase='';
 function progress(key,message){if(phase!==key&&attempt===startAttempt){phase=key;connectionPanel(message,false,true)}}
 startingStudio=true;$('engine-connect').disabled=true;$('engine-connect').textContent='앱 열기 확인…';
 progress('launch','1/3 · 브라우저의 앱 열기 확인을 허용하세요. 창이 뜨지 않아도 미설치로 단정할 수 없습니다. 아래 설치·복구 안내를 확인할 수 있습니다.');
 try{
  // Keep URI activation in the initial click, before any asynchronous network probe.
  const a=document.createElement('a');a.href='localvoicestudio://start?origin='+encodeURIComponent(location.origin)+'&nonce='+nonce;a.hidden=true;document.body.append(a);a.click();a.remove();
  while(Date.now()<deadline&&attempt===startAttempt){
   try{
    const health=await sessionFetch('/health');if(attempt!==startAttempt)return;
    if(health.service!=='local-voice-bridge'||health.protocol!==2||(health.version&&health.version!=='1.4.0')){showStartHelp('이전 버전 또는 다른 엔진이 응답합니다. 작업을 마친 뒤 기존 트레이 엔진을 종료하고 다시 시도하세요.');return}
    progress('approval','2/3 · 엔진 응답을 확인했습니다. 로컬 승인 창에 표시된 사이트 주소를 확인하고 승인하세요.');
    $('engine-connect').textContent='연결 승인 대기…';
    if(!pendingToken){const result=await sessionFetch('/connect',{nonce});pendingToken=result.token;}
    if(attempt!==startAttempt){if(pendingToken)sessionFetch('/release',{},pendingToken).catch(()=>{});return}
    progress('status','3/3 · 승인이 완료됐습니다. 엔진 환경을 확인합니다.');
    token=pendingToken;await initialize(()=>attempt===startAttempt);
    if(attempt!==startAttempt){sessionFetch('/release',{},pendingToken).catch(()=>{});return}
    if(!serverReady)throw Error('승인 후 엔진 환경 확인에 실패했습니다.');
    $('engine-connect').textContent='엔진 연결됨';$('engine-connect').classList.add('connected');$('engine-disconnect').hidden=false;
    $('connection-notice').hidden=true;$('error').textContent='';return;
   }catch(e){
    if(attempt!==startAttempt)return;
    if(e.status===403&&!pendingToken)progress('approval','2/3 · 엔진이 응답합니다. 로컬 승인 창이 열려 있다면 사이트 주소를 확인하고 승인하세요. 창이 없으면 설치·연결 복구를 확인하세요.');
    else if(Date.now()-started>=8000&&!pendingToken)progress('no-response','엔진 응답이 아직 없습니다. 앱 열기 취소, 실행 링크 미등록, 권한 차단, 구버전 실행 등이 원인일 수 있습니다. 설치·복구 안내를 열거나 취소 후 다시 시도하세요.');
    await new Promise(resolve=>setTimeout(resolve,1000));
   }
  }
  if(attempt===startAttempt){if(pendingToken)sessionFetch('/release',{},pendingToken).catch(()=>{});showStartHelp('45초 안에 연결을 완료하지 못했습니다. 계속 기다리지 않아도 됩니다. 처음 사용자는 설치하고, 기존 사용자도 아래 설치·복구 프로그램에서 연결 복구를 선택하세요. 브라우저의 로컬 네트워크 권한도 확인하세요.');}
 }finally{
  if(attempt===startAttempt){startingStudio=false;$('engine-connect').disabled=false;if(!serverReady)$('engine-connect').textContent='스튜디오 시작'}
 }
}
function clearStudioConnection(){serverReady=false;token='';$('engine-connect').textContent='스튜디오 시작';$('engine-connect').classList.remove('connected');$('engine-disconnect').hidden=true;}
async function disconnectStudio(){
 if(busy){stage('작업 완료 후 연결을 해제하세요.');return}
 try{if(token)await sessionFetch('/release',{},token)}catch{}
 clearStudioConnection();stage('이 탭의 연결을 해제했습니다. 다른 탭과 진행 중인 작업이 없으면 엔진이 자동 종료합니다.');
}
async function heartbeat(){
 if(!token||heartbeatBusy||startingStudio)return;heartbeatBusy=true;
 try{await sessionFetch('/lease',{},token)}catch{clearStudioConnection();showStartHelp('엔진 연결이 끊겼습니다. 다시 시작해 주세요. 현재 대본은 유지됩니다.');}
 finally{heartbeatBusy=false}
}
setInterval(heartbeat,20000);
window.addEventListener('pagehide',()=>{
 if(!token)return;
 fetch(engineBase+'/release',{method:'POST',headers:{'Content-Type':'application/json','X-App-Token':token},body:'{}',keepalive:true,targetAddressSpace:'loopback'}).catch(()=>{});
});
window.addEventListener('pageshow',e=>{if(e.persisted)heartbeat()});window.addEventListener('focus',heartbeat);
