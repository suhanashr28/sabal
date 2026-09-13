(async()=>{
 const form=document.querySelector('form'),heading=document.querySelector('.login-box h2'),submit=form.querySelector('button[type=submit]');
 const username=form.querySelector('input[type=text]'),password=form.querySelector('input[type=password]'),remember=form.querySelector('input[type=checkbox]');
 const toggle=form.querySelector('.password-toggle');
 toggle.addEventListener('click',()=>{const visible=password.type==='password';password.type=visible?'text':'password';toggle.setAttribute('aria-label',visible?'Hide password':'Show password');toggle.setAttribute('aria-pressed',String(visible));toggle.querySelector('.eye-slash').toggleAttribute('hidden',!visible);});
 username.name='username';username.autocomplete='username';username.setAttribute('aria-label','Username');password.name='password';password.setAttribute('aria-label','Password');
 const status=document.createElement('p');status.setAttribute('role','status');status.style.color='#ffb3c0';form.append(status);submit.disabled=true;
 let registering=false;
 const signup=document.querySelector('.signup');
 const switchMode=document.createElement('button');switchMode.type='button';switchMode.className='account-switch';signup.replaceChildren(switchMode);
 function renderMode(){heading.textContent=registering?'Create your account':'Sign In';submit.textContent=registering?'Create account':'Sign In';password.autocomplete=registering?'new-password':'current-password';password.minLength=registering?10:1;switchMode.textContent=registering?'Already have an account? Sign in':'New to LoveFlix? Create account';document.querySelector('.note').textContent=registering?'Use at least 10 characters for your password. All accounts share this site’s memories, profiles, and editing access.':'Sign in with your own account to open our shared memories.';status.textContent='';}
 switchMode.onclick=()=>{registering=!registering;password.value='';renderMode();};
 try{const state=await LF.api('/api/setup-state');registering=state.needsSetup;renderMode();document.querySelector('.options a')?.remove();submit.disabled=false;}catch(error){status.textContent='Start the LoveFlix server with npm start, then refresh this page.';switchMode.disabled=true;}
 form.onsubmit=async event=>{event.preventDefault();submit.disabled=true;switchMode.disabled=true;status.textContent='';try{await LF.save(registering?'/api/register':'/api/login','POST',{username:username.value,password:password.value,remember:remember.checked});location.href='/profile.html';}catch(error){status.textContent=error.message;}finally{submit.disabled=false;switchMode.disabled=false;}};
})();
