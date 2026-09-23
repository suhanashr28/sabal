(() => {
 const button=document.getElementById('play-surprise');
 if(!button)return;
 button.addEventListener('click',async()=>{
  const LF=window.LF;
  await LF.ready;
  if(!LF.state){LF.notify('Please log in to watch your surprise.');return;}
  const video=LF.state.media.filter(item=>!item.deleted&&item.kind==='video'&&item.collections.includes('surprise')).at(-1);
  if(video){LF.openMedia(video);return;}
  LF.addMedia('surprise');
 });
})();
