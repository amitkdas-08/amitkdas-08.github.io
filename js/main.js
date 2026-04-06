document.addEventListener('DOMContentLoaded',()=>{
  const t=document.querySelector('.nav-toggle'),n=document.querySelector('.nav-links');
  if(t&&n){t.addEventListener('click',()=>n.classList.toggle('open'));document.addEventListener('click',e=>{if(!e.target.closest('.nav'))n.classList.remove('open')})}
  const nav=document.querySelector('.nav');
  if(nav)window.addEventListener('scroll',()=>nav.classList.toggle('scrolled',window.scrollY>10));
  const p=window.location.pathname.split('/').pop()||'index.html';
  document.querySelectorAll('.nav-links a').forEach(a=>{const h=a.getAttribute('href');if(h===p||(p===''&&h==='index.html'))a.classList.add('active')});
  const obs=new IntersectionObserver(e=>{e.forEach(en=>{if(en.isIntersecting){en.target.style.animationPlayState='running';obs.unobserve(en.target)}})},{threshold:.1});
  document.querySelectorAll('.fade-in').forEach(el=>{el.style.animationPlayState='paused';obs.observe(el)});
  document.querySelectorAll('.filter-group').forEach(g=>{const b=g.querySelector('.filter-btn'),d=g.querySelector('.filter-dropdown');if(!b||!d)return;b.addEventListener('click',e=>{e.stopPropagation();document.querySelectorAll('.filter-dropdown.open').forEach(x=>{if(x!==d)x.classList.remove('open')});d.classList.toggle('open')})});
  document.addEventListener('click',()=>document.querySelectorAll('.filter-dropdown.open').forEach(d=>d.classList.remove('open')));
  document.querySelectorAll('.sub-tab').forEach(tab=>{tab.addEventListener('click',()=>{const tgt=tab.dataset.tab;document.querySelectorAll('.sub-tab').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));tab.classList.add('active');const c=document.getElementById(tgt);if(c)c.classList.add('active')})});
});
function applyFilters(){
  const af={};document.querySelectorAll('.active-filter-tag').forEach(t=>{const tp=t.dataset.filterType;if(!af[tp])af[tp]=[];af[tp].push(t.dataset.filterValue)});
  const cards=document.querySelectorAll('.pub-item');let v=0;
  const hasFilters=Object.keys(af).length>0;
  cards.forEach(c=>{let show=true;if(hasFilters){for(const[tp,vals]of Object.entries(af)){const cv=c.dataset[tp];if(cv&&!vals.includes(cv)){show=false;break}}}c.style.display=show?'':'none';if(show)v++});
  document.querySelectorAll('.pub-year-group').forEach(g=>{const vc=g.querySelectorAll('.pub-item:not([style*="display: none"])');g.style.display=vc.length>0?'':'none'});
  const ci=document.querySelector('.pub-count');if(ci)ci.textContent='Showing '+v+' of '+cards.length+' publications';
  const nr=document.querySelector('.no-results');if(nr)nr.style.display=v===0?'block':'none';
}
function addFilter(type,value){
  const c=document.querySelector('.active-filters');if(!c)return;
  if(c.querySelector('[data-filter-type="'+type+'"][data-filter-value="'+value+'"]'))return;
  const t=document.createElement('button');t.className='active-filter-tag';t.dataset.filterType=type;t.dataset.filterValue=value;t.innerHTML=value+' ✕';
  t.addEventListener('click',()=>{t.remove();applyFilters()});c.appendChild(t);applyFilters();
  document.querySelectorAll('.filter-dropdown.open').forEach(d=>d.classList.remove('open'));
}
function clearAllFilters(){const c=document.querySelector('.active-filters');if(c)c.innerHTML='';applyFilters()}
