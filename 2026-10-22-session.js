/* A user gesture starts the installed handler. No tray, persistent token or automatic program launch. */
let startingStudio=false,heartbeatBusy=false;
function showStartHelp(message){
 connectionError(message);
 const n=$('connection-notice');
 const p=document.createElement('p');p.textContent='이미 설치했다면 앱 열기 확인과 로컬 승인 창을 확인하세요. 브라우저의 로컬 네트워크 접근 권한도 확인하세요.';n.append(p);
 const a=document.createElement('a');a.href='./manual.html#install';a.target='_blank';a.rel='noopener';a.textContent='처음 사용자: 설치 방법 보기';n.append(a);
}
async function sessionFetch(path,data,auth=''){
 const c=new AbortController(),timer=setTimeout(()=>c.abort(),4000);
 try{
  const r=await fetch(engineBase+path,{method:'POST',headers:{'Content-Type':'application/json',...(auth?{'X-App-Token':auth}:{})},body:JSON.stringify(data),targetAddressSpace:'loopback',signal:c.signal});
  const v=await r.json();if(!r.ok)throw Error(v.error||'엔진 응답 오류');return v;
 }finally{clearTimeout(timer)}
}
async function startStudio(required=false){
 if(startingStudio)return;
 if(serverReady){stage('엔진 연결됨 · 마지막 탭이 닫히면 작업 완료 후 자동 종료합니다.');return}
 if(location.protocol==='file:'){showStartHelp('HTML 직접 열기 대신 배포 웹 주소로 접속하세요.');return}
 startingStudio=true;
 const nonce=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
 $('engine-connect').disabled=true;$('engine-connect').textContent='엔진 시작 중…';
 connectionError('앱 열기 확인 후 로컬 창에서 이 사이트를 승인하세요. 설치된 환경을 사용하며 자동으로 재설치하지 않습니다.');
 // Dispatch synchronously in the click event. A failed HTTP probe must not consume activation first.
 const a=document.createElement('a');a.href='localvoicestudio://start?origin='+encodeURIComponent(location.origin)+'&nonce='+nonce;a.hidden=true;document.body.append(a);a.click();a.remove();
 let lastError='';
 try{
  const deadline=Date.now()+90000;
  while(Date.now()<deadline){
   try{
    const connected=await sessionFetch('/connect',{nonce});token=connected.token;
    await initialize();
    if(!serverReady)throw Error('엔진 초기 상태를 읽지 못했습니다.');
    $('engine-connect').textContent='엔진 연결됨';$('engine-connect').classList.add('connected');$('engine-disconnect').hidden=false;
    $('connection-notice').hidden=true;$('error').textContent='';return;
   }catch(e){lastError=e.message;await new Promise(r=>setTimeout(r,1500))}
  }
  showStartHelp('엔진 연결을 완료하지 못했습니다. 미설치로 판정한 것은 아닙니다. '+lastError);
 }finally{startingStudio=false;$('engine-connect').disabled=false;if(!serverReady)$('engine-connect').textContent='스튜디오 시작'}
}
function clearStudioConnection(){serverReady=false;token='';$('engine-connect').textContent='스튜디오 시작';$('engine-connect').classList.remove('connected');$('engine-disconnect').hidden=true;}
async function disconnectStudio(){
 if(busy){stage('작업 완료 후 연결을 해제하세요.');return}
 try{if(token)await sessionFetch('/release',{},token)}catch{}
 clearStudioConnection();stage('이 탭의 연결을 해제했습니다. 다른 탭과 진행 중인 작업이 없으면 엔진이 자동 종료합니다.');
}
async function heartbeat(){
 if(!token||heartbeatBusy)return;heartbeatBusy=true;
 try{await sessionFetch('/lease',{},token)}catch{clearStudioConnection();showStartHelp('엔진 연결이 끊겼습니다. 스튜디오 시작으로 다시 연결하세요. 대본은 유지됩니다.');}
 finally{heartbeatBusy=false}
}
setInterval(heartbeat,20000);
window.addEventListener('pagehide',()=>{
 if(!token)return;
 fetch(engineBase+'/release',{method:'POST',headers:{'Content-Type':'application/json','X-App-Token':token},body:'{}',keepalive:true,targetAddressSpace:'loopback'}).catch(()=>{});
});
window.addEventListener('pageshow',e=>{if(e.persisted)heartbeat()});
window.addEventListener('focus',heartbeat);
