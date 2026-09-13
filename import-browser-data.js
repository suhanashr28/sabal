(() => {
 LF.ready.then(()=>{
  if(!LF.state || !location.pathname.endsWith('settings.html'))return;
  const section=LF.el('section','','setting');section.append(LF.el('h2','Earlier browser saves'),LF.el('p','If you saved favorites or uploaded files in an earlier version on this same browser address, import them here. Existing files are kept.'));
  const button=LF.el('button','Import browser saves','lf-action'),status=LF.el('p');status.setAttribute('role','status');section.append(button,status);document.querySelector('main').append(section);
  button.onclick=async()=>{
   button.disabled=true;let imported=0;
   const read=key=>{try{return JSON.parse(localStorage.getItem(key));}catch{return null;}};
   try{
    for(const profile of ['my','sabal']){
     for(const item of read(`lf-favorites-${profile}`)||[]){if(!item.id||!item.title||!item.href)continue;await LF.save(`/api/favorites/${profile}`,'PUT',item);imported++;}
     const picture=read(`lf-picture-${profile}`),marker=`lf-imported-picture-${profile}`;
     if(picture?.startsWith('data:image/')&&localStorage.getItem(marker)!==picture){const blob=await(await fetch(picture)).blob();const file=new File([blob],'profile.jpg',{type:blob.type});const media=await LF.upload(file,'profile');const p=LF.state.profiles.find(x=>x.id===profile);await LF.save(`/api/profiles/${profile}`,'PATCH',{name:p.name,picture:media.url});localStorage.setItem(marker,picture);imported++;}
    }
    const databases=await indexedDB.databases?.()||[];
    if(databases.some(x=>x.name==='loveflix-videos')){
     const db=await new Promise((resolve,reject)=>{const req=indexedDB.open('loveflix-videos');req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
     if(db.objectStoreNames.contains('videos'))for(let index=1;index<=6;index++){
      const id=`video-${index}`;const file=await new Promise((resolve,reject)=>{const req=db.transaction('videos').objectStore('videos').get(id);req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
      if(!file)continue;const signature=`${file.name}:${file.size}:${file.lastModified}`;const marker=`lf-imported-${id}`;if(localStorage.getItem(marker)===signature)continue;
      await LF.upload(file,'videos',null,p=>status.textContent=`Importing ${file.name}: ${p}%`);localStorage.setItem(marker,signature);imported++;
     }
     db.close();
    }
    await LF.refresh();LF.render();status.textContent=imported?`${imported} browser saves imported. Refresh Settings to see all imported files.`:'No earlier saves were found at this browser address.';
   }catch(error){status.textContent=`${imported} imported. ${error.message}`;}finally{button.disabled=false;}
  };
 });
})();
