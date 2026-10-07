/* TOEIC 800 · 毎日背单词 — study helpers (no dependencies) */
(function(){
  var LS={get:function(k,d){try{var v=localStorage.getItem(k);return v===null?d:JSON.parse(v);}catch(e){return d;}},
          set:function(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}};
  var root=document.documentElement, body=document.body;
  var T={
    zh:{prog:function(a,b){return '已掌握 '+a+'/'+b;},done:function(a,b){return '✓ 已掌握 '+a+'/'+b;},
        play:'▶ 全部播放',stop:'⏹ 停止',qn:function(i,n){return '第 '+i+' / '+n+' 题';},
        e2m:'选出正确的意思',m2e:'选出对应的英文单词',next:'下一题 →',finish:'查看结果',
        score:function(a,b){return '答对 '+a+' / '+b;},again:'🔄 再来一组',missed:'需要复习：',perfect:'全对！太棒了 🎉',start:'开始测验'},
    ja:{prog:function(a,b){return '習得 '+a+'/'+b;},done:function(a,b){return '✓ 習得 '+a+'/'+b;},
        play:'▶ 全部再生',stop:'⏹ 停止',qn:function(i,n){return '第 '+i+' 問 / '+n;},
        e2m:'正しい意味を選んでください',m2e:'対応する英単語を選んでください',next:'次へ →',finish:'結果を見る',
        score:function(a,b){return a+' / '+b+' 問正解';},again:'🔄 もう一度',missed:'復習しよう：',perfect:'全問正解！🎉',start:'テスト開始'}
  };
  function lang(){return root.classList.contains('ja')?'ja':'zh';}
  function t(k){return T[lang()][k];}
  var hooks=[];
  function setLang(l){
    root.classList.toggle('ja',l==='ja'); root.lang=l==='ja'?'ja':'zh-CN';
    try{localStorage.setItem('tv.lang',l);}catch(e){}
    [].forEach.call(document.querySelectorAll('.langsw button'),function(b){b.classList.toggle('on',b.dataset.lang===l);});
    hooks.forEach(function(f){f();});
  }
  document.addEventListener('click',function(ev){var b=ev.target.closest&&ev.target.closest('.langsw button'); if(b) setLang(b.dataset.lang);});
  setLang(lang());

  /* ---------- index page: per-day progress ---------- */
  [].forEach.call(document.querySelectorAll('a.ep[data-day]'),function(a){
    var m=LS.get('tv.m.day'+a.dataset.day,[]), el=a.querySelector('.done');
    function draw(){ if(el) el.textContent=m.length?t('done')(m.length,+a.dataset.total):''; }
    draw(); hooks.push(draw);
  });

  var wd=document.getElementById('wdata'); if(!wd) return;
  var DATA=JSON.parse(wd.textContent), DAY=DATA.day, WORDS=DATA.words;
  var cards=[].slice.call(document.querySelectorAll('li.wd'));

  /* ---------- audio: one shared Audio element, play() inside the tap handler (iOS-safe), as on toeic800 ---------- */
  var au=new Audio(); au.preload='none'; var cur=null, queue=null, qi=0, qtimer=null;
  function clear(){ if(cur){cur.classList.remove('playing'); cur=null;} }
  function play(btn){ clear(); au.src=new URL(btn.dataset.src,location.href).href; au.currentTime=0;
    var p=au.play(); cur=btn; btn.classList.add('playing'); if(p&&p.catch) p.catch(function(){clear(); if(queue) stopAll();}); }
  au.addEventListener('ended',function(){ clear(); if(queue){ qtimer=setTimeout(step,450); } });
  au.addEventListener('pause',function(){ if(!au.ended) clear(); });
  au.addEventListener('error',function(){ clear(); if(queue){ qtimer=setTimeout(step,200); } });
  document.addEventListener('click',function(ev){
    var b=ev.target.closest&&ev.target.closest('button.say'); if(!b) return;
    ev.stopPropagation();
    if(queue) stopAll();
    if(cur===b&&!au.paused){au.pause();return;}
    play(b);
  },true);

  /* ---------- play all: word → example → next word ---------- */
  var tPlay=document.getElementById('tPlay');
  function setPlayLabel(){ tPlay.innerHTML=queue?t('stop'):t('play'); tPlay.classList.toggle('on',!!queue); }
  hooks.push(setPlayLabel);
  function step(){
    if(!queue) return;
    if(qi>=queue.length){ stopAll(); return; }
    var b=queue[qi++], li=b.closest('li.wd');
    cards.forEach(function(c){c.classList.toggle('now',c===li);});
    if(b.classList.contains('sm')===false) li.scrollIntoView({behavior:'smooth',block:'center'});
    play(b);
  }
  function stopAll(){ queue=null; clearTimeout(qtimer); au.pause(); clear(); cards.forEach(function(c){c.classList.remove('now');}); setPlayLabel(); }
  tPlay.addEventListener('click',function(){
    if(queue){ stopAll(); return; }
    queue=[]; qi=0;
    cards.forEach(function(li){ if(li.offsetParent===null) return; [].forEach.call(li.querySelectorAll('button.say'),function(b){queue.push(b);}); });
    setPlayLabel(); step();
  });

  /* ---------- mastered (localStorage) ---------- */
  var MK='tv.m.day'+DAY, done=LS.get(MK,[]);
  var prog=document.getElementById('prog');
  function drawProg(){ prog.textContent=t('prog')(done.length,cards.length); }
  hooks.push(drawProg);
  [].forEach.call(document.querySelectorAll('.mk input'),function(cb){
    var w=cb.dataset.w, li=cb.closest('li.wd');
    cb.checked=done.indexOf(w)>=0; li.classList.toggle('done',cb.checked);
    cb.addEventListener('change',function(){
      var i=done.indexOf(w); if(cb.checked&&i<0) done.push(w); if(!cb.checked&&i>=0) done.splice(i,1);
      LS.set(MK,done); li.classList.toggle('done',cb.checked); drawProg();
    });
  });
  drawProg();

  /* ---------- hide meanings (self-quiz) & only-unmastered filter ---------- */
  function toggler(id,cls,key){
    var b=document.getElementById(id), on=LS.get(key,false);
    function apply(){ body.classList.toggle(cls,on); b.classList.toggle('on',on); }
    b.addEventListener('click',function(){ on=!on; LS.set(key,on); if(cls==='quiz') cards.forEach(function(c){c.classList.remove('rev');}); apply(); });
    apply();
  }
  toggler('tHide','quiz','tv.hide'); toggler('tTodo','todo','tv.todo');
  cards.forEach(function(li){ li.addEventListener('click',function(ev){
    if(!body.classList.contains('quiz')) return;
    if(ev.target.closest('button,label,input,a')) return;
    li.classList.toggle('rev');
  }); });

  /* ---------- 10-question quiz ---------- */
  var box=document.getElementById('quizBox'), Q=[], qn=0, score=0, answered=false, wrong=[];
  function shuffle(a){ for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1)),x=a[i];a[i]=a[j];a[j]=x;} return a; }
  function esc(s){ return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
  function newQuiz(){
    var pool=shuffle(WORDS.slice()).slice(0,10);
    Q=pool.map(function(w,i){
      var opts=shuffle(WORDS.filter(function(x){return x.w!==w.w;})).slice(0,3).concat([w]);
      return {w:w, type:i%2?'m2e':'e2m', opts:shuffle(opts)};
    });
    qn=0; score=0; wrong=[]; render();
  }
  function audioBtn(w){ return '<button type="button" class="say sm" data-src="audio/day'+DAY+'/'+w.s+'.mp3" aria-label="play">🔊</button>'; }
  function render(){
    if(!Q.length){ box.innerHTML='<button type="button" class="btn" id="qStart">'+t('start')+'</button>'; return; }
    if(qn>=Q.length){
      var h='<div class="score">'+t('score')(score,Q.length)+'</div>';
      h+= wrong.length? '<div>'+t('missed')+'</div><ul class="miss">'+wrong.map(function(w){return '<li><a href="#w-'+w.s+'"><b>'+esc(w.w)+'</b></a> — '+esc(w[lang()])+'</li>';}).join('')+'</ul>' : '<div>'+t('perfect')+'</div>';
      box.innerHTML=h+'<div class="qbar"><span></span><button type="button" class="btn" id="qAgain">'+t('again')+'</button></div>'; return;
    }
    var q=Q[qn], L=lang();
    var head = q.type==='e2m' ? '<div class="qq">'+esc(q.w.w)+' '+audioBtn(q.w)+'</div><div class="qh">'+t('e2m')+'</div>'
                              : '<div class="qq" lang="'+(L==='ja'?'ja':'zh')+'">'+esc(q.w[L])+'</div><div class="qh">'+t('m2e')+'</div>';
    var opts=q.opts.map(function(o,i){ return '<button type="button" class="opt" data-i="'+i+'"'+(q.type==='e2m'&&L==='ja'?' lang="ja"':'')+'>'+String.fromCharCode(65+i)+'. '+esc(q.type==='e2m'?o[L]:o.w)+'</button>'; }).join('');
    box.innerHTML='<div class="qn">'+t('qn')(qn+1,Q.length)+'</div>'+head+'<div class="opts">'+opts+'</div><div class="qbar"><span class="qn">'+score+' ✓</span><button type="button" class="btn" id="qNext" style="visibility:hidden">'+(qn+1<Q.length?t('next'):t('finish'))+'</button></div>';
    answered=false;
  }
  box.addEventListener('click',function(ev){
    var b=ev.target.closest('button'); if(!b||b.classList.contains('say')) return;
    if(b.id==='qStart'||b.id==='qAgain'){ newQuiz(); return; }
    if(b.id==='qNext'){ qn++; render(); return; }
    if(b.classList.contains('opt')&&!answered){
      answered=true; var q=Q[qn], pick=q.opts[+b.dataset.i];
      [].forEach.call(box.querySelectorAll('.opt'),function(o){ if(q.opts[+o.dataset.i].w===q.w.w) o.classList.add('ok'); });
      if(pick.w===q.w.w) score++; else { b.classList.add('ng'); wrong.push(q.w); }
      document.getElementById('qNext').style.visibility='visible';
      play({dataset:{src:'audio/day'+DAY+'/'+q.w.s+'.mp3'},classList:{add:function(){},remove:function(){}}});
    }
  });
  hooks.push(function(){ if(Q.length) render(); else render(); });
  render();
})();
