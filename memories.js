const memories = {
  'first-date': { number: '01', title: 'Our First Date', photo: 'images/us-2.jpeg', lead: 'The day our story became real — full of nerves, smiles, and the feeling that something beautiful was beginning.', heading: 'Story of our first date', story: 'I still smile when I think of our first date. I was excited and nervous, but being with you made everything feel easy. Every conversation, every little smile, and every moment of that day became a memory I will always keep close to my heart.' },
  'story-begins': { number: '02', title: 'Our Story Begins', photo: 'images/us-3.jpeg', lead: 'Every hello led to us, and every small moment became part of something so special.', heading: 'The beginning of us', story: 'Our story did not begin with a grand plan. It began in the small moments: a conversation, a laugh, and the comfort of getting to know each other. Somehow, those little moments grew into the love story I never want to stop living.' },
  'best-part': { number: '03', title: 'The Best Part', photo: 'images/us-4.jpeg', lead: 'The best part of every day is knowing I get to share it with you.', heading: 'My favorite part', story: 'The best part is never where we go or what we do — it is you. Your smile, your presence, and the way even ordinary moments feel special when we are together are the things I treasure most.' },
  birthday: { number: '05', title: 'Birthday Celebration', photo: 'images/birthday-01.jpeg', lead: 'A celebration for my favorite person, filled with love, smiles, and a memory worth replaying.', heading: 'Celebrating you', story: 'Your birthday is a reminder of how grateful I am that you are here and that I get to love you. I hope this celebration holds all the happiness, warmth, and love you deserve today and always.', video: true },
  family: { number: '06', title: 'Family', photo: 'images/family-01.jpeg', lead: 'The kind of love that makes every place feel like home.', heading: 'Love that feels like home', story: 'Family is made of the people who bring comfort, laughter, and warmth into our lives. This photo is a little reminder of the love around us and the beautiful memories we get to share.' },
  airport: { number: '07', title: 'Airport', photo: 'images/airport-03.jpeg', lead: 'Every trip, every goodbye, and every return carries a piece of our story.', heading: 'A message for every goodbye', story: 'Airports always make my heart feel so many things at once. There is the excitement of a new journey, the sadness of saying goodbye, and the quiet hope of seeing you again soon. Even when distance makes the moment hard, it never changes what you mean to me. I carry our memories with me wherever I go, and I look forward to the next hug, the next laugh, and the next time we are together. Until then, please remember that you are loved more than these words can say.' }
};
const photoSets = {
  'first-date': [2, 8, 14, 20, 26],
  'story-begins': [3, 9, 15, 21, 27],
  'best-part': [4, 10, 16, 22, 28],
  birthday: [5, 11, 17, 23, 29],
  family: [6, 12, 18, 24, 30],
  airport: [7, 13, 19, 25, 31]
};
const key = new URLSearchParams(location.search).get('memory');
if (key === 'first-date') location.replace('memory-details.html');
if (key === 'story-begins') location.replace('story-begins.html');
if (key === 'best-part') location.replace('best-part.html');
const memory = memories[key] || memories['first-date'];
document.title = `${memory.title} — LoveFlix`;
document.querySelector('#memory-number').textContent = `MEMORY ${memory.number}`;
document.querySelector('#memory-title').textContent = memory.title;
document.querySelector('#memory-photo').src = memory.photo;
document.querySelector('#memory-photo').alt = memory.title;
document.querySelector('#memory-lead').textContent = memory.lead;
document.querySelector('#story-heading').textContent = memory.heading;
document.querySelector('#memory-story').textContent = memory.story;
document.querySelector('#memory-photos').innerHTML = (photoSets[key] || photoSets['first-date']).map((number) => `<img src="images/us-${number}.jpeg" alt="${memory.title} memory">`).join('');
if (memory.video) {
  document.body.classList.add('birthday-memory');
  document.querySelector('#memory-photos').innerHTML = Array.from({length: 12}, (_, index) => `<img src="images/birthday-${String(index + 1).padStart(2, '0')}.jpeg" alt="Birthday celebration photo ${index + 1}" loading="lazy">`).join('');
  document.querySelector('#birthday-video').hidden = false;
  const video = document.querySelector('#birthday-video video');
  video.poster = 'images/birthday-01.jpeg';
  video.preload = 'metadata';
  video.setAttribute('playsinline', '');
}

if (key === 'family') {
  document.body.classList.add('family-memory');
  document.querySelector('#memory-photos').innerHTML = Array.from({length: 14}, (_, index) => `<img src="images/family-${String(index + 1).padStart(2, '0')}.jpeg" alt="Family memory ${index + 1}" loading="lazy">`).join('');
}

if (key === 'airport') {
  document.body.classList.add('airport-memory');
  document.querySelector('#memory-lead').textContent = 'My mind knew you were leaving. My heart was still asking for a little longer.';
  document.querySelector('#story-heading').textContent = 'My mind was ready. My heart was not.';
  const letter = document.createElement('div');
  letter.id = 'memory-story';
  const paragraphs = ["My love,", "I thought I was ready. My mind knew you were leaving. It understood the plans, the reasons, and the future waiting for you. I had told myself so many times that this day would come. But my heart never caught up. It kept treating your departure like something far away, something we still had time before. And then suddenly, I was standing beside you at the airport, wishing that understanding something could make it hurt less.", "That goodbye was one of the hardest moments of my life. You were right there, close enough for me to hold, and I was already missing you. I wanted to stay in that small space beside you for a little longer. Another minute. Another hug. A little more time before I had to learn what my days would feel like without being able to see you whenever I missed you.", "When I look at these pictures, I see us trying to smile. I am grateful we have them, but there is so much a photograph cannot hold. It cannot show every word I swallowed, or how badly I wanted the world to slow down. It cannot explain how I could be standing beside my favorite person and still feel the ache of the distance that was about to come between us. I wish I could step back into one of these photos, just long enough to hold you again.", "I wanted to be brave for you. I wanted you to look at me and feel loved, supported, and proud of everything ahead of you. And I did feel proud. I still do. But beneath all of that was a much smaller, softer wish: please, let me have a little more time with him. I knew there was no amount of time that would make saying goodbye easy. Even so, my heart kept asking.", "There were so many ordinary things I suddenly wanted. Sitting beside you with nothing special to say. Hearing you laugh without a phone between us. Looking up and finding you there. The little moments I used to think we could always have again felt so precious that day. If I could have packed anything for myself, it would have been a few more of those moments to keep for the evenings when missing you becomes too much.", "I think that is what made it so hard. I was saying goodbye to the familiar comfort of having you close. I had to let go of your hand while every part of me still wanted to hold it. My mind could tell me that we would talk, that we would find our way through this, that distance did not erase our love. My heart could only feel that, for a while, it would have to love you from somewhere your arms could not reach.", "Some days I will probably miss you quietly. I will see something funny and wish I could turn straight to you. I will have a long day and want the kind of hug that lets me stop explaining. I will look through these pictures and remember how it felt to stand beside you. On other days, I will tell you I miss you again, even if I told you an hour before. Sometimes those three words are the closest I can get to saying, “There is a place beside me that still feels like yours.”", "Please do not carry my sadness as guilt. I want you to live fully where you are. Make friends, learn things, laugh loudly, eat properly, and let yourself enjoy the life you are building. I want to hear about the small, happy parts of your day as much as the difficult ones. Loving you means I can ache to have you here and still be glad when something beautiful happens for you there.", "And when you have a hard day, you do not have to find perfect words for me. Tell me you are tired. Tell me you miss home. Tell me something silly or sit with me on a call for a while. I cannot always make the distance smaller, but I can listen. I want us to keep making room for each other, even as our days become different. I want to know the person you are becoming and keep sharing the person I am becoming, too.", "Since 27 April 2023, you have become part of so many memories I treasure. That airport goodbye belongs to our story now, too, even though it is a part I can hardly look at without feeling it all over again. I wish it had been easier. I wish I had known how to say everything in my heart while you were still beside me. So I am putting some of it here, for you to read whenever you need to feel close to me.", "I love you. I was not ready to miss you this much, but I love you. I am proud of you, even on the days when being strong feels difficult. I am grateful for us, even when the distance makes me cry. And I am looking forward to a day when seeing you does not mean looking at a screen, when I can finally put my arms around you and take my time letting go.", "Until then, let us keep choosing the little things that bring us closer. The messages, the calls, the honest conversations, the patience when one of us is tired. We do not have to make every day perfect. I just want us to keep finding each other in the middle of it all.", "My mind knew how to say, “Have a safe flight.” My heart was still saying, “A little longer, please.”", "I think a part of me is still there, holding on to that last hug. And another part is already waiting for the next one.", "I love you, baby. Across the distance, through the ordinary days, and all the way to the moment I get to see you again. ♡"];
  paragraphs.forEach(text => { const paragraph = document.createElement('p'); paragraph.textContent = text; letter.append(paragraph); });
  document.querySelector('#memory-story').replaceWith(letter);
  document.querySelector('#memory-photos').innerHTML = Array.from({length: 8}, (_, i) => `<img src="images/airport-${String(i+1).padStart(2,'0')}.jpeg" alt="Airport memory ${i+1}" loading="lazy">`).join('');
  const section = document.createElement('section');
  section.className = 'video-section airport-videos';
  section.innerHTML = '<h2>Our airport moments</h2>' + Array.from({length:3}, (_, i) => `<div class="airport-video"><h3>Airport memory ${i+1}</h3><video controls playsinline preload="metadata" poster="images/airport-${String(i+1).padStart(2,'0')}.jpeg" aria-label="Airport video ${i+1}"><source src="videos/airport-${String(i+1).padStart(2,'0')}.mp4" type="video/mp4"></video></div>`).join('');
  document.querySelector('main').append(section);
}

// Keep every memory's videos alongside its photos in the same gallery.
const mediaGrid = document.querySelector('#memory-photos');
const memoryVideos = [...document.querySelectorAll('.video-section video')].filter(video => !video.closest('[hidden]'));
if (memoryVideos.length) {
  const photos = [...mediaGrid.children];
  mediaGrid.classList.add('mixed-media-grid');
  document.querySelector('.memory-gallery h2').textContent = 'Photos & videos';
  memoryVideos.forEach((video, index) => {
    video.setAttribute('aria-label', `${memory.title} video ${index + 1}`);
    const photo = photos[Math.floor(index * photos.length / memoryVideos.length)];
    photo.after(video);
  });
  document.querySelectorAll('.video-section').forEach(section => section.remove());
}
