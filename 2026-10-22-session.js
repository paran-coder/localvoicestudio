/* Explicit activation; bounded status checks; no installation inference from network failure. */
let startingStudio=false,heartbeatBusy=false,startAttempt=0;
function connectionPanel(message,error=false,waiting=false){
 const n=$('connection-notice');n.hidden=false;n.replaceChildren();n.classList.toggle('connection-warning',error);
 n.setAttribute('role',error?'alert':'status');const p=document.createElement('p');p.textContent=message;n.append(p);
 const actions=document.createElement('div');actions.className='connection-actions';
 const control=document.createElement('button');control.type='button';control.textContent=waiting?'시작 취소':'다시 연결';control.onclick=waiting?cancelStudioStart:()=>startStudio();actions.append(control);
 if(!waiting&&error){const download=document.createElement('a');download.className='secondary-button';download.href='./downloads/2026-10-22-Local-Voice-Studio-Setup-v1.4.0.exe';download.download='';download.textContent='최신 설치기 다운로드';download.onclick=showDownloadSteps;actions.append(download);}n.append(actions);
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
 $('onboarding').hidden=true;$('onboarding').open=false;
}
async function startStudio(required=false){
 if(startingStudio)return;
 if(location.protocol==='file:'){showStartHelp('이 파일을 직접 열어서는 엔진에 연결할 수 없습니다. 배포된 웹 주소에서 스튜디오 시작을 눌러주세요.');return}
 const attempt=++startAttempt;
 const nonce=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
 let pendingToken='',launched=false,launchTime=0;
 const current=()=>attempt===startAttempt;
 const progress=message=>{if(current())connectionPanel(message,false,true)};
 const compatible=h=>h.service==='local-voice-bridge'&&h.protocol===2;
 function launch(force=false){
  if(!current()||(launched&&!force))return;
  launched=true;launchTime=Date.now();
  const a=document.createElement('a');a.href='localvoicestudio://start?origin='+encodeURIComponent(location.origin)+'&nonce='+nonce;a.hidden=true;document.body.append(a);a.click();a.remove();
  progress('엔진을 준비하고 있습니다. 앱 열기와 사이트 승인 창이 나타나면 승인하세요. 첫 실행에는 시간이 걸릴 수 있으며, 준비되면 자동으로 연결합니다.');
 }
 function manualLaunch(){
  const b=document.createElement('button');b.type='button';b.textContent='엔진 실행 허용';b.onclick=()=>launch(true);b.className='engine-launch-action';$('connection-notice').querySelector('.connection-actions').append(b);
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
  let deadline=Date.now()+120000;
  let misses=0;
  while(current()&&Date.now()<(launched?launchTime+120000:deadline)){
   if(!launched){await new Promise(r=>setTimeout(r,1000));if(Date.now()>deadline-112000){showStartHelp('아직 엔진 실행이 허용되지 않았습니다. 다시 시도하거나 아래에서 상황에 맞는 항목을 선택하세요.');return;}continue;}
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
    if(e.status===403){misses=0;progress('엔진이 응답합니다. 로컬 사이트 승인 창이 나타났다면 주소를 확인하고 승인하세요.');}
    else if(!pendingToken){misses++;if(misses===2)progress('엔진 준비를 기다리고 있습니다. 승인 창에서 예를 눌렀다면 다시 시작하지 말고 기다려주세요. 준비가 끝나면 자동 연결됩니다.');}
    await new Promise(r=>setTimeout(r,1000));
   }
  }
  if(current())showStartHelp('연결을 완료하지 못했습니다. 설치를 완료했다면 실행 승인과 브라우저 권한을 확인한 뒤 다시 연결하세요. 처음 설치하거나 설치 도중 실패했다면 최신 설치기를 다운로드하세요.');
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
 $('download-steps').textContent='다운로드 목록에서 방금 받은 최신 EXE를 열고 설치 시작을 선택하세요. 설치 도중 실패한 경우도 설치 시작으로 다시 검사합니다. 로컬 준비 확인 완료가 나오면 웹으로 돌아와 스튜디오 시작을 누르세요.';
}
function showConnectionHelp(){
 if(startingStudio)cancelStudioStart();
 $('onboarding').hidden=false;$('onboarding').open=true;
 connectionPanel('설치 도중 실패했다면 최신 설치기를 받아 설치 시작으로 다시 검사하세요. 설치를 완료했는데 연결되지 않을 때는 실행 승인·브라우저 권한을 먼저 확인하고, 계속 실패할 때만 연결 복구를 사용하세요.',true,false);
 $('onboarding').scrollIntoView({behavior:'smooth',block:'start'});
}
