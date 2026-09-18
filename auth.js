(() => {
 const params=new URLSearchParams(location.search);
 let mode=['register','forgot','reset'].includes(params.get('mode'))?params.get('mode'):'login';
 const token=new URLSearchParams(location.hash.slice(1)).get('token')||'';
 if(token)history.replaceState(null,'',location.pathname+'?mode=reset');
 const form=document.getElementById('account-form'),heading=document.getElementById('account-title'),status=document.getElementById('account-status'),submit=document.getElementById('account-submit');
 const fields={name:form.elements.name,email:form.elements.email,phone:form.elements.phone,identity:form.elements.identity,password:form.elements.password,confirm:form.elements.confirm};
 const routes={register:['name','email','phone','password','confirm'],login:['identity','password'],forgot:['email'],reset:['password','confirm']};
 const titles={register:'Create your account',login:'Log in',forgot:'Forgot password?',reset:'Choose a new password'};
 const labels={register:'Create account',login:'Log in',forgot:'Send reset link',reset:'Save new password'};
 function render(){
  heading.textContent=titles[mode];submit.textContent=labels[mode];document.title=titles[mode]+' — LoveFlix';
  Object.entries(fields).forEach(([key,input])=>{const visible=routes[mode].includes(key);input.closest('.input-group').hidden=!visible;input.disabled=!visible;input.required=visible;});
  fields.password.minLength=mode==='login'?1:10;fields.password.autocomplete=mode==='login'?'current-password':'new-password';
  document.getElementById('remember-row').hidden=mode!=='login';document.getElementById('forgot-link').hidden=mode!=='login';
  document.getElementById('login-link').hidden=mode==='login';document.getElementById('register-link').hidden=mode!=='login';
  document.getElementById('register-note').hidden=mode!=='register';
  if(mode==='reset'&&!token){status.textContent='This reset link is incomplete. Please request a new link.';submit.disabled=true;}
  if(mode==='login'&&params.get('created'))status.textContent='Account created. Log in with your email and password.';
 }
 document.querySelectorAll('.password-toggle').forEach(button=>button.addEventListener('click',()=>{const input=document.getElementById(button.getAttribute('aria-controls'));const show=input.type==='password';input.type=show?'text':'password';button.textContent=show?'Hide':'Show';button.setAttribute('aria-label',show?'Hide password':'Show password');button.setAttribute('aria-pressed',String(show));}));
 form.addEventListener('submit',async event=>{
  event.preventDefault();status.textContent='';
  if((mode==='register'||mode==='reset')&&fields.password.value!==fields.confirm.value){status.textContent='Passwords do not match.';fields.confirm.focus();return;}
  submit.disabled=true;
  try{
   const data=Object.fromEntries(routes[mode].map(key=>[key,fields[key].value]));delete data.confirm;
   if(mode==='reset')data.token=token;
   if(mode==='login')data.remember=form.elements.remember.checked;
   const response=await fetch('/api/accounts/'+mode,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
   const result=await response.json();if(!response.ok)throw Error(result.error||'Please try again.');
   if(mode==='register'){location.assign('/login.html?created=1');return;}
   if(mode==='login'){location.assign('/profile.html');return;}
   if(mode==='reset'){fields.password.value='';fields.confirm.value='';status.textContent='Password updated. You can now log in.';submit.hidden=true;return;}
   status.textContent=result.message;
  }catch(error){status.textContent=error.message==='Failed to fetch'?'Unable to connect. Check your internet connection and try again.':error.message;}
  finally{submit.disabled=false;}
 });
 render();
})();
