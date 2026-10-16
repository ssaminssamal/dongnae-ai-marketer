let pendingInstall;
const installButton=document.querySelector('#install');
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();pendingInstall=event;installButton.hidden=false;});
installButton.addEventListener('click',async()=>{if(!pendingInstall)return;await pendingInstall.prompt();const choice=await pendingInstall.userChoice;if(choice.outcome==='accepted')installButton.hidden=true;pendingInstall=null;});
window.addEventListener('appinstalled',()=>{installButton.hidden=true;pendingInstall=null;});
const instructions=document.querySelector('#instructions');
document.querySelector('#help').addEventListener('click',()=>{
 const ios=/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
 document.querySelector('#platform').textContent=ios?'아이폰·아이패드: Safari에서 이 주소를 열고 공유 → 홈 화면에 추가를 선택하세요.':'PC·안드로이드: Chrome 또는 Edge 메뉴의 앱 설치·홈 화면에 추가를 선택하세요. 설치 버튼이 나타나면 바로 눌러도 됩니다.';
 instructions.showModal();
});
document.querySelector('#close').addEventListener('click',()=>instructions.close());
function onlineState(){document.body.classList.toggle('offline',!navigator.onLine);}
window.addEventListener('online',onlineState);window.addEventListener('offline',onlineState);onlineState();
if('serviceWorker' in navigator&&window.isSecureContext){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
