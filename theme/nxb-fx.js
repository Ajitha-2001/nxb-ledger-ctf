/* NXB theme effects: red code-rain background (#rain) and typewriter line ([data-type]). Pure cosmetic, no network. */
(function(){
  var calm=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var t=document.querySelector('[data-type]');
  if(t){var s=t.getAttribute('data-type');if(calm){t.textContent=s}else{var i=0;(function k(){t.textContent=s.slice(0,++i);if(i<s.length)setTimeout(k,32)})()}}
  var c=document.getElementById('rain');if(!c||calm)return;
  var x=c.getContext('2d'),f=16,cols,drops,ch='01ABCDEF<>/\\{}[]#$%&*+=NXB';
  function size(){c.width=innerWidth;c.height=innerHeight;cols=Math.ceil(c.width/f);drops=[];for(var i=0;i<cols;i++)drops[i]=Math.random()*-50}
  size();addEventListener('resize',size);
  setInterval(function(){
    x.fillStyle='rgba(6,5,6,.16)';x.fillRect(0,0,c.width,c.height);x.font=f+'px monospace';
    for(var i=0;i<cols;i++){
      x.fillStyle=Math.random()>.97?'#fff':'#ff2a44';
      x.fillText(ch[Math.floor(Math.random()*ch.length)],i*f,drops[i]*f);
      if(drops[i]*f>c.height&&Math.random()>.975)drops[i]=0;drops[i]++;
    }
  },60);
})();
