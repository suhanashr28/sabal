(() => {
  const start = Date.UTC(2023, 3, 27);
  function updateDays() {
    const now = new Date();
    const year = now.getFullYear();
    const today = Date.UTC(year, now.getMonth(), now.getDate());
    const days = Math.max(0, Math.round((today - start) / 86400000));
    const anniversary = Date.UTC(year, 3, 27);
    const years = Math.max(0, year - 2023 - (today < anniversary ? 1 : 0));
    const nextYear = Math.max(2024, today < anniversary ? year : year + 1);
    const remaining = Math.round((Date.UTC(nextYear, 3, 27) - today) / 86400000);
    document.querySelector('#relationship-days').textContent = days.toLocaleString('en-US');
    document.querySelector('#relationship-years').textContent = `${years} ${years === 1 ? 'year' : 'years'} together ♡`;
    document.querySelector('#relationship-next').textContent = `${today === anniversary && years > 0 ? 'Happy anniversary! ' : ''}${remaining} ${remaining === 1 ? 'day' : 'days'} until ${nextYear - 2023} years together · 27 April ${nextYear}`;
  }
  updateDays();
  setInterval(updateDays, 30000);
  document.addEventListener('visibilitychange', updateDays);
})();
