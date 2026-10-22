/* Explicit activation; bounded status checks; no installation inference from network failure. */
let startingStudio=false,heartbeatBusy=false,startAttempt=0;
function connectionPanel(message,error=false,waiting=false){
 const n=$('connection-notice');n.hidden=false;n.replaceChildren();n.classList.toggle('connection-warning',error);
 n.setAttribute('role',error?'alert':'status');const p=document.createElement('p');p.textContent=message;n.append(p);
 const actions=document.createElement('div');actions.className='connection-actions';
 const control=document.createElement('button');control.type='button';control.textContent=waiting?'시작 취소':'다시 시도';control.onclick=waiting?cancelStudioStart:()=>startStudio();actions.append(control);
 const a=document.createElement('a');a.className='secondary-button';a.href='./manual.html#install';a.target='_blank';a.rel='noopener';a.textContent='자세한 안내';const download=document.createElement('a');download.className='secondary-button';download.href='./downloads/2026-10-22-Local-Voice-Studio-Setup-v1.4.0.exe';download.download='';download.textContent='설치 프로그램 다운로드';download.onclick=showDownloadSteps;const help=document.createElement('button');help.type='button';help.textContent='연결 문제 해결';help.onclick=showConnectionHelp;if(!waiting&&error){download.textContent="처음 사용 · 설치하기";actions.append(help);actions.append(download);actions.append(a);}n.append(actions);
 stage(message,error);
}
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
function showStartHelp(message){
 connectionPanel(message,true,false);
 $('onboarding').hidden=false;$('onboarding').hidden=false;$('onboarding').open=true;
}
async function startStudio(required=false){
 if(startingStudio)return;
 if(location.protocol==='file:'){showStartHelp('이 파일을 직접 열어서는 엔진에 연결할 수 없습니다. 배포된 웹 주소에서 스튜디오 시작을 눌러주세요.');return}
 const attempt=++startAttempt;
 const nonce=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
 let pendingToken='',launched=false;
 const current=()=>attempt===startAttempt;
 const progress=message=>{if(current())connectionPanel(message,false,true)};
 const compatible=h=>h.service==='local-voice-bridge'&&h.protocol===2;
 function launch(force=false){
  if(!current()||(launched&&!force))return;
  launched=true;
  const a=document.createElement('a');a.href='localvoicestudio://start?origin='+encodeURIComponent(location.origin)+'&nonce='+nonce;a.hidden=true;document.body.append(a);a.click();a.remove();
  progress('엔진 실행·연결을 요청했습니다. 앱 실행 확인 창이 나타나면 열기를 선택하세요. 이미 설치했다면 다시 설치할 필요는 없습니다.');
 }
 function manualLaunch(){
  const b=document.createElement('button');b.type='button';b.textContent='엔진 실행 허용';b.onclick=()=>launch(true);$('connection-notice').append(b);
 }
 async function finish(auth){
  if(!current())return false;
  token=auth;await initialize(current);
  if(!current())return false;
  if(!serverReady)throw Error('상태 확인 실패');
  $('engine-connect').textContent='엔진 연결됨';$('engine-connect').classList.add('connected');$('engine-disconnect').hidden=false;
  $('connection-notice').hidden=true;$('onboarding').hidden=true;$('onboarding').open=false;$('error').textContent='';return true;
 }
 startingStudio=true;$('engine-connect').disabled=true;$('engine-connect').textContent='연결 확인 중…';
 progress('사용 가능한 로컬 엔진 연결을 확인하고 있습니다.');
 try{
  // Reuse valid authorization. Never launch or suggest installation for a healthy connection.
  if(token){
   try{await sessionFetch('/lease',{},token);if(await finish(token))return;}catch{}
   if(!current())return;
   clearStudioConnection();
  }
  try{
   const health=await sessionFetch('/health');if(!current())return;
   if(!compatible(health)){showStartHelp('다른 종류 또는 이전 연결 방식의 엔진이 응답합니다. 설치하지 말고 먼저 연결 문제 해결에서 현재 실행 상태를 확인하세요.');return}
   progress('실행 중인 엔진을 찾았습니다. 이 웹사이트의 사용 승인을 요청합니다.');
  }catch{if(!current())return;progress('엔진이 아직 응답하지 않아 설치된 실행기에 시작을 요청합니다.');}
  // A slow probe/permission dialog may consume browser activation. In that case request a real click.
  if(typeof navigator!=='undefined'&&navigator.userActivation&&!navigator.userActivation.isActive){
   progress('브라우저에서 프로그램을 열려면 한 번 더 확인이 필요합니다. 아래 엔진 실행 허용을 눌러주세요.');manualLaunch();
  }else{launch();manualLaunch();}
  const deadline=Date.now()+35000;
  while(current()&&Date.now()<deadline){
   if(!launched){await new Promise(r=>setTimeout(r,1000));continue;}
   try{
    const h=await sessionFetch('/health');if(!current())return;
    if(!compatible(h)){showStartHelp('호환되는 연결 엔진이 아닙니다. 연결 문제 해결에서 실행 상태를 확인하세요.');return}
    if(!pendingToken){
     const auth=await sessionFetch('/connect',{nonce});pendingToken=auth.token;
     if(!current()){sessionFetch('/release',{},pendingToken).catch(()=>{});return;}
    }
    if(await finish(pendingToken))return;
   }catch(e){
    if(!current())return;
    if(e.status===403)progress('엔진이 응답합니다. 로컬 사이트 승인 창이 나타났다면 주소를 확인하고 승인하세요.');
    await new Promise(r=>setTimeout(r,1000));
   }
  }
  if(current())showStartHelp('연결을 완료하지 못했습니다. 처음 사용하는 경우 설치하기를 선택하고, 설치한 적이 있다면 연결 문제 해결을 선택하세요. 연결 실패만으로 재설치할 필요는 없습니다.');
 }finally{
  if(pendingToken&&(!current()||!serverReady))sessionFetch('/release',{},pendingToken).catch(()=>{});
  if(current()){startingStudio=false;$('engine-connect').disabled=false;if(!serverReady)$('engine-connect').textContent='스튜디오 시작';}
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

function showDownloadSteps(){
 if(startingStudio)cancelStudioStart();
 $('onboarding').hidden=false;$('onboarding').open=true;
 $('download-steps').textContent='다운로드가 끝나면 브라우저 다운로드 목록에서 받은 EXE 파일을 열어주세요. 설치 창에서 설치 시작을 선택하고, 완료 후 이 페이지의 스튜디오 시작을 누르세요.';
}
function showConnectionHelp(){
 if(startingStudio)cancelStudioStart();
 $('onboarding').hidden=false;$('onboarding').open=true;
 connectionPanel('설치한 사용자라면 먼저 앱 열기·로컬 승인 창을 확인하고, 브라우저의 로컬 네트워크 접근 허용 여부를 확인하세요. 기존 엔진이 다른 폴더에서 실행 중이라면 그 작업을 마친 뒤 종료하고 다시 시도하세요. 그래도 연결되지 않을 때만 설치 프로그램의 연결 복구를 사용하세요. 재설치부터 하지 않아도 됩니다.',true,false);
 $('onboarding').scrollIntoView({behavior:'smooth',block:'start'});
}
