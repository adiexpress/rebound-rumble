'use strict';
const el=id=>document.getElementById(id);
let cards={}, selection=[null,null], fighters=[], moves=[null,null], chooser=0, round=1, phase='setup';
let stream=null, facing='environment';
let scanActive=false, scanning=false, scanTimer=null, recentDetections=[], lastScanLabel='';
async function init(){cards=await (await fetch('/data/cards')).json();bind();}
function bind(){
 el('manualBtn').onclick=()=>el('manual').classList.toggle('hidden');
 document.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>register(b.dataset.id));
 el('start').onclick=startBattle;
 el('openCamera').onclick=()=>openCamera();el('closeCamera').onclick=closeCamera;
 el('capture').onclick=()=>{recentDetections=[];scanFrame()};
 el('switchCamera').onclick=()=>{facing=facing==='environment'?'user':'environment';openCamera()};
 el('continue').onclick=()=>{el('handoff').classList.add('hidden');el('choice').classList.remove('hidden');chooser=1;renderChoices()};
 el('nextRound').onclick=()=>{round++;moves=[null,null];chooser=0;el('roundDone').classList.add('hidden');el('choice').classList.remove('hidden');renderChoices()};
 el('restart').onclick=reset;el('playAgain').onclick=reset;
}
function register(id){
 if(!cards[id]){el('setupMessage').textContent='This card is not in the two-card demo database.';return}
 if(selection.includes(id)){el('setupMessage').textContent=`${cards[id].symbol} was already registered. Scan the other card.`;return}
 let slot=selection.findIndex(x=>x===null);if(slot<0)return;
 selection[slot]=id;let c=cards[id];el('slot'+slot).innerHTML=`<div class="loaded"><img src="${c.image}" alt="${c.name} card"><strong>${c.name}</strong><small>${c.symbol} · ${c.role}</small></div>`;
 el('setupMessage').textContent=slot===0?'Player 1 loaded. Now scan Player 2.':'Both fighters are ready!';
 el('start').disabled=selection.some(x=>x===null);
}
async function openCamera(){
 closeCamera();el('modal').classList.remove('hidden');el('capture').disabled=true;
 el('scanStatus').textContent='Requesting camera permission…';
 try{
  stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:facing},width:{ideal:1280},height:{ideal:720}}});
  el('video').srcObject=stream;
  await el('video').play();
  el('cameraFrame').style.aspectRatio=`${el('video').videoWidth} / ${el('video').videoHeight}`;
  scanActive=true;recentDetections=[];lastScanLabel='';
  el('capture').disabled=false;
  el('capture').textContent='RECHECK NOW';
  el('scanStatus').textContent='Align one entire card inside the yellow outline…';
  // Start recognition automatically, without any Capture button press.
  scanTimer=setTimeout(scanFrame,120);
 }catch(e){
  el('scanStatus').textContent='Camera unavailable: '+e.message+'. Use Manual Test Mode if needed.';
 }
}
function closeCamera(){
 scanActive=false;clearTimeout(scanTimer);
 if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}
 el('modal').classList.add('hidden');
}
async function scanFrame(){
 if(!scanActive || scanning) return;
 const video=el('video');
 if(!stream || !video.videoWidth) {if(scanActive)scanTimer=setTimeout(scanFrame,300);return}
 scanning=true;
 try{
  // Crop only the fixed card guide (+small margin), avoiding an expensive
  // full-frame card search.  Guide height = 78% of displayed video height;
  // its physical aspect ratio is 5/7.  Both have the same aspect ratio as
  // the underlying video because cameraFrame uses video metadata.
  const canvas=document.createElement('canvas');
  const vh=video.videoHeight, vw=video.videoWidth;
  const guideH=vh*0.78, guideW=guideH*5/7;
  const margin=1.14;
  const cropH=Math.min(vh,guideH*margin), cropW=Math.min(vw,guideW*margin);
  canvas.width=420;
  canvas.height=Math.round(420*cropH/cropW);
  canvas.getContext('2d',{alpha:false}).drawImage(video,
    (vw-cropW)/2,(vh-cropH)/2,cropW,cropH,
    0,0,canvas.width,canvas.height);
  const blob=await new Promise(r=>canvas.toBlob(r,'image/jpeg',0.69));
  if(!blob)throw new Error('Could not capture camera frame');
  const response=await fetch('/api/scan?guided=1',{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob});
  if(!response.ok)throw new Error('Scanner returned '+response.status);
  const result=await response.json();
  if(!scanActive)return;
  // Require 2 agreeing readings in 3 frames to avoid one-frame false positives.
  // An unclear frame does not force a possibly incorrect identification.
  recentDetections.push(result.ok ? result.cardId : null);
  if(recentDetections.length>3)recentDetections.shift();
  const counts={};
  for(const id of recentDetections)if(id)counts[id]=(counts[id]||0)+1;
  const match=Object.keys(counts).find(id=>counts[id]>=2);
  if(match){
   if(selection.includes(match)){
    recentDetections=[];
    el('scanStatus').textContent='Already scanned '+cards[match].symbol+' - show the other card.';
   }else{
    register(match);
    closeCamera();
    return;
   }
  }else if(result.ok){
   el('scanStatus').textContent='Detected '+result.label+' - hold steady to confirm...';
  }else{
   el('scanStatus').textContent=result.message || 'Scanning continuously…';
  }
 }catch(e){
  if(scanActive)el('scanStatus').textContent='Scan error: '+e.message+'. Retrying automatically…';
 }finally{
  scanning=false;
  if(scanActive)scanTimer=setTimeout(scanFrame,95);
 }
}
function startBattle(){if(selection.some(x=>!x))return;
 fighters=selection.map(id=>{let c=cards[id];return {...c,currentHp:c.hp,charge:0,ultimateUsed:false}});
 round=1;chooser=0;moves=[null,null];phase='battle';el('setup').classList.add('hidden');el('battle').classList.remove('hidden');
 el('log').textContent='Both fighters enter the arena. Player 1 chooses first.';renderFighters();renderChoices();}
function renderFighters(){el('roundTitle').textContent='ROUND '+round;
 fighters.forEach((f,i)=>{let hp=Math.max(0,100*f.currentHp/f.hp),meter=Math.max(0,100*f.charge/55);
 el('fight'+i).innerHTML=`<div class="subtitle">PLAYER ${i+1} · ${f.symbol} · ${f.role}</div><h3>${f.name}</h3><img src="${f.image}" alt="${f.name}"><div class="statline"><b>HP</b><span>${f.currentHp} / ${f.hp}</span></div><div class="track"><div class="hpbar" style="width:${hp}%"></div></div><div class="statline"><b>BOUNCE BACK</b><span>${f.charge} / 55</span></div><div class="track"><div class="meterbar" style="width:${meter}%"></div></div><div class="ready">${f.ultimateUsed?'ULTIMATE USED':f.charge>=55?'BOUNCE BACK READY!':'&nbsp;'}</div><div class="statrow">ATK ${f.attack} · DEF ${f.defense} · SPD ${f.speed} · CRIT ${Math.round(f.critChance*100)}%</div>`})}
function renderChoices(){const f=fighters[chooser];el('choiceTitle').textContent=`PLAYER ${chooser+1} / CHOOSE YOUR MOVE`;el('choiceHint').textContent=`${f.name} · lock in secretly`;
 el('moveInfo').textContent='Your move stays hidden until both players choose.';
 el('moves').innerHTML='';
 for(const key of ['quick','heavy','guard','ultimate']){const m=f.moves[key];const btn=document.createElement('button');btn.className='move '+(key==='ultimate'?'ultimate':'');
 btn.disabled=key==='ultimate'&&(f.charge<55||f.ultimateUsed);
 btn.innerHTML=`<strong>${m.name}</strong><small>${m.description}</small>${key==='ultimate'?'<small>55 charge · once per battle</small>':''}`;
 btn.onclick=()=>pickMove(key);el('moves').appendChild(btn)}
}
function pickMove(move){moves[chooser]=move;el('choice').classList.add('hidden');
 if(chooser===0){el('handoff').classList.remove('hidden');el('handoffTitle').textContent='PASS TO PLAYER 2';}
 else resolveRound()}
function damage(attacker,defender,move,guarded){
 let power=attacker.moves[move].power;
 let amount=Math.max(1,Math.floor(power*attacker.attack/(attacker.attack+defender.defense)));
 const crit=Math.random()<attacker.critChance;if(crit)amount=Math.floor(amount*1.5);
 if(guarded)amount=Math.max(1,Math.floor(amount*.4));
 amount=Math.min(amount,defender.currentHp);defender.currentHp-=amount;
 if(!defender.ultimateUsed)defender.charge=Math.min(55,defender.charge+amount);
 return {amount,crit};
}
function resolveRound(){
 const order=[0,1].sort((i,j)=>{
 const pi=fighters[i].moves[moves[i]].priority,pj=fighters[j].moves[moves[j]].priority;
 if(pi!==pj)return pj-pi;
 const di=fighters[j].speed-fighters[i].speed;return di|| (Math.random()<.5?-1:1);
 });
 const guard=[moves[0]==='guard',moves[1]==='guard'];
 let entries=[`Round ${round}: ${fighters[0].name} chose ${fighters[0].moves[moves[0]].name}; ${fighters[1].name} chose ${fighters[1].moves[moves[1]].name}.`];
 for(const i of order){const a=fighters[i],d=fighters[1-i],m=moves[i];if(a.currentHp<=0)continue;
 if(m==='guard'){entries.push(`${a.name} guarded, reducing damage taken this round.`);continue}
 if(m==='ultimate'){if(a.charge<55||a.ultimateUsed){entries.push(a.name+' could not activate their ultimate.');continue}a.charge=0;a.ultimateUsed=true;}
 const hit=damage(a,d,m,guard[1-i]);entries.push(`${a.name} used ${a.moves[m].name} and dealt ${hit.amount} damage${hit.crit?' (CRITICAL HIT!)':''}.`);
 if(d.currentHp<=0){entries.push(`${d.name} is knocked out!`);break}
 if(d.charge>=55&&!d.ultimateUsed)entries.push(`${d.name} unlocked BOUNCE BACK!`);
 }
 renderFighters();el('log').innerHTML=entries.map(x=>`<div>${escapeHTML(x)}</div>`).join('');
 const alive=fighters.map(f=>f.currentHp>0);
 if(!alive[0]||!alive[1]){el('result').classList.remove('hidden');el('resultTitle').textContent=!alive[0]&&!alive[1]?'DRAW!':`${fighters[alive[0]?0:1].name} WINS!`;
 el('resultSubtitle').textContent='Battle complete. Scan again to face a new challenger.';
 }else el('roundDone').classList.remove('hidden');
}
function escapeHTML(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function reset(){closeCamera();selection=[null,null];fighters=[];moves=[null,null];chooser=0;round=1;phase='setup';
 el('battle').classList.add('hidden');el('setup').classList.remove('hidden');
 ['choice','handoff','roundDone','result'].forEach(id=>el(id).classList.add('hidden'));
 ['slot0','slot1'].forEach((id,i)=>el(id).innerHTML=`<div class="empty"><div class="empty-symbol">+</div><strong>PLAYER ${i+1}</strong><small>AWAITING CARD</small></div>`);
 el('start').disabled=true;el('setupMessage').textContent='Scan J♥ and A♣ / either order.';
}
init().catch(e=>{el('setupMessage').textContent='Error loading card database: '+e.message});
