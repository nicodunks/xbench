/* Xbench v2 hero: a shaft of light from the top right, dust that catches it,
   and sparks when a card turns. Three.js, orthographic, pixel-mapped to the hero. */
(function(){
  if(!window.THREE)return;
  const hero=document.querySelector('.hero'),mural=document.getElementById('muralGrid');
  if(!hero)return;
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canvas=document.createElement('canvas');canvas.className='hero-light';hero.prepend(canvas);
  const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:false,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.75));
  renderer.setClearColor(0x000000,0);
  const scene=new THREE.Scene();
  let W=1,H=1;const camera=new THREE.OrthographicCamera(0,1,0,-1,-100,100);
  const T={time:0,src:new THREE.Vector2(),target:new THREE.Vector2(),mouse:new THREE.Vector2(0,0),hasMouse:false};

  /* ---------- the light: rays, cone, halo ---------- */
  const rayMat=new THREE.ShaderMaterial({
    transparent:true,depthWrite:false,depthTest:false,blending:THREE.AdditiveBlending,
    uniforms:{uRes:{value:new THREE.Vector2(1,1)},uSrc:{value:new THREE.Vector2()},uTime:{value:0},uAngle:{value:-2.35},uSpread:{value:0.80},uMural:{value:new THREE.Vector4(0,0,0,0)}},
    vertexShader:`varying vec2 vP;void main(){vP=vec2(position.x,-position.y);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`
      precision highp float;varying vec2 vP;uniform vec2 uRes,uSrc;uniform float uTime,uAngle,uSpread;uniform vec4 uMural;
      float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
      float adiff(float a,float b){float d=a-b;return abs(atan(sin(d),cos(d)));}
      float peak(float x,float p){return pow(0.5+0.5*sin(x),p);}
      void main(){
        vec2 d=vP-uSrc;float dist=length(d)+1.0;vec2 dir=d/dist;float ang=atan(dir.y,dir.x);
        float k=adiff(ang,uAngle);
        float cone=1.0-smoothstep(uSpread*0.55,uSpread,k);
        float t=uTime*0.06;
        /* a fan of rays: wide soft bands, narrow bright shafts, and a crisp per-ray brightness */
        float wide=peak(ang*22.0-t*0.6+0.8,2.5);
        float mid=peak(ang*61.0+t,5.0);
        float fine=peak(ang*150.0-t*1.7,12.0);
        float bin=floor((ang+t*0.12)*96.0);
        float crisp=smoothstep(0.30,0.95,hash(vec2(bin,3.7)));
        float crispEdge=peak((ang+t*0.12)*96.0*6.28318/6.28318*1.0,1.0);
        float rays=0.22*wide+0.55*mid*(0.35+0.65*wide)+0.75*fine*crisp+0.35*crisp*peak((ang+t*0.12)*96.0,3.0);
        rays*=0.65+0.35*sin(dist*0.004-uTime*0.5+bin);
        /* rays keep going across the whole section, fading gently */
        float reach=1.0/(1.0+dist/(uRes.y*1.35));
        float along=dot(d,vec2(cos(uAngle),sin(uAngle)));
        float beam=cone*reach;
        float shaft=rays*cone*reach*2.4+beam*0.28;
        float halo=exp(-dist/(uRes.y*0.24))*2.4+exp(-dist/(uRes.y*0.07))*3.2+exp(-dist/(uRes.y*0.02))*5.0;
        vec2 m0=uMural.xy,m1=uMural.zw;vec2 q=clamp(vP,m0,m1);float md=length(vP-q);
        float pool=exp(-md/110.0)*beam*0.45;
        float a=shaft+halo+pool;
        /* the light passes over the cards: keep the text readable */
        float onMural=1.0-step(0.5,md);a*=mix(1.0,0.55,onMural);
        a+=(hash(vP+uTime)-0.5)*0.015;
        /* yellow-white at the source and inside the shafts, gold at the edges */
        vec3 gold=vec3(1.0,0.80,0.46),cream=vec3(1.0,0.96,0.82),white=vec3(1.0,0.99,0.94);
        float hot=clamp(rays*cone,0.0,1.0);
        vec3 col=mix(gold,cream,hot);
        col=mix(col,white,clamp(halo*0.35,0.0,1.0));
        gl_FragColor=vec4(col*a,clamp(a,0.0,1.0));
      }`
  });
  const rayMesh=new THREE.Mesh(new THREE.PlaneGeometry(1,1),rayMat);scene.add(rayMesh);

  /* ---------- dust that catches the light ---------- */
  const N=reduce?0:1400;
  const dustGeo=new THREE.BufferGeometry();
  const seed=new Float32Array(N*4);for(let i=0;i<N;i++){seed[i*4]=Math.random();seed[i*4+1]=Math.random();seed[i*4+2]=Math.random();seed[i*4+3]=Math.random()}
  dustGeo.setAttribute('position',new THREE.BufferAttribute(new Float32Array(N*3),3));
  dustGeo.setAttribute('seed',new THREE.BufferAttribute(seed,4));
  const dustMat=new THREE.ShaderMaterial({
    transparent:true,depthWrite:false,depthTest:false,blending:THREE.AdditiveBlending,
    uniforms:{uRes:{value:new THREE.Vector2(1,1)},uSrc:{value:new THREE.Vector2()},uTime:{value:0},uAngle:{value:-2.35},uSpread:{value:0.80},uPR:{value:1}},
    vertexShader:`
      attribute vec4 seed;uniform vec2 uRes,uSrc;uniform float uTime,uAngle,uSpread,uPR;varying float vA;varying float vStar;
      float adiff(float a,float b){float d=a-b;return abs(atan(sin(d),cos(d)));}
      void main(){
        float t=uTime;
        float x=seed.x*uRes.x+sin(t*0.13+seed.w*6.28)*18.0+cos(t*0.07+seed.z*6.28)*9.0;
        float y=mod(seed.y*uRes.y-t*(4.0+seed.z*9.0),uRes.y+40.0)-20.0;
        vec2 p=vec2(x,y);vec2 d=p-uSrc;float dist=length(d)+1.0;float ang=atan(d.y/dist,d.x/dist);
        float cone=1.0-smoothstep(uSpread*0.3,uSpread,adiff(ang,uAngle));
        float reach=exp(-dist/(uRes.y*1.1));
        float tw=0.5+0.5*sin(t*(1.2+seed.w*2.4)+seed.x*31.0);
        tw=pow(tw,3.0);
        vA=(0.05+cone*reach*1.6)*(0.2+0.8*tw);
        vStar=step(0.86,seed.z)*tw;
        float s=(1.2+seed.w*2.2+vStar*4.0)*uPR;
        gl_PointSize=s*(1.0+cone*reach*1.5);
        gl_Position=projectionMatrix*modelViewMatrix*vec4(p.x,-p.y,0.0,1.0);
      }`,
    fragmentShader:`
      precision highp float;varying float vA;varying float vStar;
      void main(){
        vec2 c=gl_PointCoord-0.5;float r=length(c)*2.0;
        float disc=smoothstep(1.0,0.2,r);
        float cross=max(smoothstep(0.08,0.0,abs(c.x))*smoothstep(1.0,0.1,abs(c.y)*2.0),smoothstep(0.08,0.0,abs(c.y))*smoothstep(1.0,0.1,abs(c.x)*2.0));
        float a=disc*vA+cross*vStar*vA*1.6;
        gl_FragColor=vec4(vec3(1.0,0.93,0.72)*a,a);
      }`
  });
  const dust=new THREE.Points(dustGeo,dustMat);dust.frustumCulled=false;scene.add(dust);

  /* ---------- sparks when a card turns ---------- */
  const SP=320;const spark={pos:new Float32Array(SP*3),vel:new Float32Array(SP*2),life:new Float32Array(SP),max:new Float32Array(SP),next:0};
  const sparkGeo=new THREE.BufferGeometry();
  sparkGeo.setAttribute('position',new THREE.BufferAttribute(spark.pos,3));
  const sparkLife=new Float32Array(SP);sparkGeo.setAttribute('life',new THREE.BufferAttribute(sparkLife,1));
  const sparkMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,depthTest:false,blending:THREE.AdditiveBlending,
    uniforms:{uPR:{value:1}},
    vertexShader:`attribute float life;uniform float uPR;varying float vL;void main(){vL=life;gl_PointSize=(2.0+8.0*life*life)*uPR;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`precision highp float;varying float vL;void main(){vec2 c=gl_PointCoord-0.5;float r=length(c)*2.0;float disc=smoothstep(1.0,0.0,r);float cross=max(smoothstep(0.07,0.0,abs(c.x)),smoothstep(0.07,0.0,abs(c.y)))*smoothstep(1.0,0.0,r*0.8);float a=(disc*0.8+cross)*vL;gl_FragColor=vec4(vec3(1.0,0.98,0.9)*a,a);}`});
  const sparks=new THREE.Points(sparkGeo,sparkMat);sparks.frustumCulled=false;scene.add(sparks);
  function burst(x,y,w,h,n){if(reduce)return;for(let k=0;k<n;k++){const i=spark.next=(spark.next+1)%SP;spark.pos[i*3]=x+Math.random()*w;spark.pos[i*3+1]=-(y+Math.random()*h);spark.pos[i*3+2]=1;const a=Math.random()*Math.PI*2,s=20+Math.random()*90;spark.vel[i*2]=Math.cos(a)*s;spark.vel[i*2+1]=Math.sin(a)*s-40;spark.max[i]=spark.life[i]=0.7+Math.random()*0.9}}
  window.addEventListener('xbench:flip',e=>{const r=e.detail;if(!r)return;const hb=hero.getBoundingClientRect();burst(r.left-hb.left,r.top-hb.top,r.width,r.height,22)});

  /* ---------- layout, pointer, loop ---------- */
  function layout(){const b=hero.getBoundingClientRect();W=Math.max(1,b.width);H=Math.max(1,b.height);renderer.setSize(W,H,false);camera.left=0;camera.right=W;camera.top=0;camera.bottom=-H;camera.updateProjectionMatrix();rayMesh.geometry.dispose();rayMesh.geometry=new THREE.PlaneGeometry(W,H);rayMesh.position.set(W/2,-H/2,0);rayMat.uniforms.uRes.value.set(W,H);dustMat.uniforms.uRes.value.set(W,H);const pr=renderer.getPixelRatio();dustMat.uniforms.uPR.value=pr;sparkMat.uniforms.uPR.value=pr;T.target.set(W*0.98,-H*0.02);T.src.copy(T.target);if(mural){const m=mural.getBoundingClientRect();rayMat.uniforms.uMural.value.set(m.left-b.left,m.top-b.top,m.right-b.left,m.bottom-b.top)}}
  new ResizeObserver(layout).observe(hero);layout();
  hero.addEventListener('pointermove',e=>{const b=hero.getBoundingClientRect();T.mouse.set((e.clientX-b.left)/W-0.5,(e.clientY-b.top)/H-0.5);T.hasMouse=true});
  hero.addEventListener('pointerleave',()=>{T.hasMouse=false});
  let last=performance.now(),visible=true;
  new IntersectionObserver(es=>{visible=es[0].isIntersecting},{threshold:0}).observe(hero);
  function frame(now){requestAnimationFrame(frame);if(!visible)return;const dt=Math.min(0.05,(now-last)/1000);last=now;T.time+=dt;
    /* the source breathes and leans toward the pointer */
    const bx=Math.sin(T.time*0.21)*14,by=Math.cos(T.time*0.17)*9,mx=T.hasMouse?T.mouse.x*-60:0,my=T.hasMouse?T.mouse.y*-30:0;
    T.target.set(W*0.98+bx+mx,-H*0.02+by+my);T.src.lerp(T.target,0.04);
    const src=new THREE.Vector2(T.src.x,-T.src.y);
    const angle=Math.atan2(H*0.9-(-T.src.y),W*0.30-T.src.x);
    rayMat.uniforms.uSrc.value.copy(src);rayMat.uniforms.uTime.value=T.time;rayMat.uniforms.uAngle.value=angle;
    dustMat.uniforms.uSrc.value.copy(src);dustMat.uniforms.uTime.value=T.time;dustMat.uniforms.uAngle.value=angle;
    for(let i=0;i<SP;i++){if(spark.life[i]<=0){sparkLife[i]=0;continue}spark.life[i]-=dt;spark.vel[i*2+1]+=-70*dt;spark.pos[i*3]+=spark.vel[i*2]*dt;spark.pos[i*3+1]+=spark.vel[i*2+1]*dt*-1;sparkLife[i]=Math.max(0,spark.life[i]/spark.max[i])}
    sparkGeo.attributes.position.needsUpdate=true;sparkGeo.attributes.life.needsUpdate=true;
    renderer.render(scene,camera)}
  if(reduce){T.time=7;frame(performance.now())}else requestAnimationFrame(frame);
})();
