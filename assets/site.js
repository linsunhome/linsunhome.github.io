(() => {
  const toggle = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-nav]');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  const search = document.querySelector('[data-paper-search]');
  const year = document.querySelector('[data-paper-year]');
  const rows = [...document.querySelectorAll('[data-paper-row]')];
  const empty = document.querySelector('[data-paper-empty]');
  const filter = () => {
    if (!rows.length) return;
    const query = (search?.value || '').trim().toLowerCase();
    const selectedYear = year?.value || '';
    let visible = 0;
    rows.forEach((row) => {
      const matchesQuery = !query || row.textContent.toLowerCase().includes(query);
      const matchesYear = !selectedYear || row.dataset.year === selectedYear;
      const show = matchesQuery && matchesYear;
      row.hidden = !show;
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  };
  search?.addEventListener('input', filter);
  year?.addEventListener('change', filter);
})();
