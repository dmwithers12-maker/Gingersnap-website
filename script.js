const service=document.getElementById('service');
const groups={'Custom Apparel':'apparelFields','3D Printing':'printFields','Vehicle Decals':'vehicleFields','Custom Products':'customFields'};
function showFields(){document.querySelectorAll('.conditional').forEach(x=>x.classList.add('hidden'));document.getElementById(groups[service.value]).classList.remove('hidden')}
service.addEventListener('change',showFields);showFields();
document.querySelectorAll('.choose').forEach(b=>b.onclick=()=>{service.value=b.dataset.service;showFields();document.getElementById('quote').scrollIntoView()});
const menu=document.querySelector('.menu'),nav=document.querySelector('.site-header nav');menu.onclick=()=>nav.classList.toggle('open');

let cart=JSON.parse(localStorage.getItem('gingersnapCart')||'[]');
const panel=document.getElementById('cartPanel'),shade=document.getElementById('shade');
function renderCart(){document.getElementById('cartCount').textContent=cart.length;document.getElementById('cartItems').innerHTML=cart.length?cart.map((x,i)=>`<div class="cart-item"><b>${x}</b><button onclick="removeItem(${i})">Remove</button></div>`).join(''):'<p>No projects added yet.</p>';localStorage.setItem('gingersnapCart',JSON.stringify(cart))}
window.removeItem=i=>{cart.splice(i,1);renderCart()};renderCart();
document.querySelectorAll('.add').forEach(b=>b.onclick=()=>{cart.push(b.dataset.item);renderCart();panel.classList.add('open');shade.classList.add('open')});
document.getElementById('cartBtn').onclick=()=>{panel.classList.add('open');shade.classList.add('open')};
function close(){panel.classList.remove('open');shade.classList.remove('open')}document.getElementById('closeCart').onclick=close;shade.onclick=close;document.getElementById('cartQuote').onclick=close;

const API_URL='/api/quotes';
document.getElementById('salesForm').addEventListener('submit',async e=>{
 e.preventDefault();
 const form=e.target, btn=document.getElementById('submitQuote'), msg=document.getElementById('formMessage');
 btn.disabled=true;btn.textContent='Sending...';msg.textContent='';
 const data=new FormData(form);data.append('project_list',JSON.stringify(cart));
 try{
   const r=await fetch(API_URL,{method:'POST',body:data});
   if(!r.ok) throw new Error('API unavailable');
   const out=await r.json();
   msg.innerHTML=`<div class="review"><b>Quote request received!</b><br>Request number: ${out.quote_id}<br>We can now route this request into GingerSnap's order workflow.</div>`;
   form.reset();service.value='Custom Apparel';showFields();cart=[];renderCart();
 }catch(err){
   // Local preview mode: stores the request on this device so the prototype remains testable.
   const obj={id:'GS-'+Date.now().toString().slice(-8),created:new Date().toISOString(),service:data.get('service'),name:data.get('name'),email:data.get('email'),phone:data.get('phone'),details:data.get('details'),vehicle:{year:data.get('vehicle_year'),make:data.get('vehicle_make'),model:data.get('vehicle_model')}};
   const leads=JSON.parse(localStorage.getItem('gingersnapDemoLeads')||'[]');leads.push(obj);localStorage.setItem('gingersnapDemoLeads',JSON.stringify(leads));
   msg.innerHTML=`<div class="review"><b>Preview mode: request captured on this device.</b><br>Request number: ${obj.id}<br><small>When the site is hosted with the included backend, this same button will send the request to GingerSnap and save it server-side.</small></div>`;
 }
 btn.disabled=false;btn.textContent='Submit Quote Request →';
});