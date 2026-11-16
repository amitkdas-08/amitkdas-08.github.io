/* Small SVG charting helpers used across the site (no dependencies).
   Each chart re-renders on container resize so text stays crisp at any width. */
const VZ = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  function el(tag, attrs = {}, parent) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  }
  function text(parent, x, y, s, attrs = {}) {
    const t = el('text', { x, y, ...attrs }, parent);
    t.textContent = s;
    return t;
  }

  let tip;
  function showTip(evt, htmlStr) {
    if (!tip) { tip = document.createElement('div'); tip.className = 'viz-tip'; document.body.appendChild(tip); }
    tip.innerHTML = htmlStr;
    tip.style.opacity = '1';
    const pad = 14, r = tip.getBoundingClientRect();
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + r.width > window.innerWidth - 8) x = evt.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = evt.clientY - r.height - pad;
    tip.style.transform = `translate(${x}px,${y}px)`;
  }
  function hideTip() { if (tip) tip.style.opacity = '0'; }
  function bindTip(node, fn) {
    node.addEventListener('mousemove', e => showTip(e, fn()));
    node.addEventListener('mouseleave', hideTip);
  }

  function responsive(container, draw) {
    let last = 0;
    const run = () => {
      const w = Math.round(container.clientWidth);
      if (!w || w === last) return;
      last = w;
      container.innerHTML = '';
      draw(w);
    };
    run();
    if ('ResizeObserver' in window) new ResizeObserver(run).observe(container);
    else window.addEventListener('resize', run);
  }

  function svgRoot(container, w, h, label) {
    return el('svg', { width: w, height: h, viewBox: `0 0 ${w} ${h}`, role: 'img', 'aria-label': label || '' }, container);
  }

  function legend(container, cats) {
    const wrap = document.createElement('div');
    wrap.className = 'viz-legend';
    for (const c of cats) {
      const s = document.createElement('span');
      s.innerHTML = `<i style="background:${c.color}"></i>${c.label}`;
      wrap.appendChild(s);
    }
    container.appendChild(wrap);
    return wrap;
  }

  /* Vertical stacked bars by year. opts: {years, series:[{key,label,color}], data:{year:{key:n}}, height, onClick, compact} */
  function stackedYears(container, opts) {
    responsive(container, w => {
      const h = opts.height || 170, m = { t: 14, r: 4, b: 22, l: opts.compact ? 4 : 24 };
      const svg = svgRoot(container, w, h, opts.label);
      const years = opts.years, iw = w - m.l - m.r, ih = h - m.t - m.b;
      const totals = years.map(y => opts.series.reduce((s, se) => s + ((opts.data[y] || {})[se.key] || 0), 0));
      const max = Math.max(...totals, 1);
      const step = iw / years.length, bw = Math.max(3, Math.min(26, step * 0.72));
      if (!opts.compact) {
        for (const v of [Math.ceil(max / 2), max]) {
          const y = m.t + ih - (v / max) * ih;
          el('line', { x1: m.l, x2: w - m.r, y1: y, y2: y, class: 'viz-grid' }, svg);
          text(svg, m.l - 6, y + 3, v, { class: 'viz-axis', 'text-anchor': 'end' });
        }
      }
      el('line', { x1: m.l, x2: w - m.r, y1: m.t + ih, y2: m.t + ih, class: 'viz-baseline' }, svg);
      const labelEvery = step < 22 ? (step < 12 ? 4 : 2) : 1;
      years.forEach((yr, i) => {
        const x = m.l + i * step + (step - bw) / 2;
        let y0 = m.t + ih;
        const g = el('g', { class: 'viz-bar' + (opts.onClick ? ' clickable' : '') }, svg);
        el('rect', { x: m.l + i * step, y: m.t, width: step, height: ih, fill: 'transparent' }, g);
        for (const se of opts.series) {
          const n = (opts.data[yr] || {})[se.key] || 0;
          if (!n) continue;
          const bh = (n / max) * ih;
          y0 -= bh;
          el('rect', { x, y: y0, width: bw, height: Math.max(bh - 1, 1), fill: se.color, rx: 1.5 }, g);
        }
        if (totals[i] && !opts.compact) text(svg, x + bw / 2, y0 - 4, totals[i], { class: 'viz-value', 'text-anchor': 'middle' });
        if (i % labelEvery === 0 || i === years.length - 1)
          text(svg, x + bw / 2, h - 6, opts.compact ? `'${String(yr).slice(2)}` : yr, { class: 'viz-axis', 'text-anchor': 'middle' });
        bindTip(g, () => {
          const rows = opts.series.map(se => [se, (opts.data[yr] || {})[se.key] || 0]).filter(r => r[1]);
          return `<b>${yr}</b> · ${totals[i]} paper${totals[i] === 1 ? '' : 's'}` +
            rows.map(([se, n]) => `<div><i style="background:${se.color}"></i>${se.label}: ${n}</div>`).join('') +
            (opts.onClick && totals[i] ? '<div class="viz-tip-hint">Click to filter</div>' : '');
        });
        if (opts.onClick && totals[i]) g.addEventListener('click', () => opts.onClick(yr));
      });
    });
  }

  /* Horizontal bars. opts: {rows:[{key,label,value,color,display}], onClick, max, labelWidth, barHeight} */
  function hbars(container, opts) {
    responsive(container, w => {
      const bh = opts.barHeight || 18, gap = 8, lw = Math.min(opts.labelWidth || 130, w * 0.42);
      const h = opts.rows.length * (bh + gap);
      const svg = svgRoot(container, w, h, opts.label);
      const max = opts.max || Math.max(...opts.rows.map(r => r.value), 1);
      const iw = w - lw - 46;
      opts.rows.forEach((r, i) => {
        const y = i * (bh + gap);
        const g = el('g', { class: 'viz-bar' + (opts.onClick ? ' clickable' : '') }, svg);
        el('rect', { x: 0, y, width: w, height: bh, fill: 'transparent' }, g);
        text(g, lw - 8, y + bh / 2 + 4, r.label, { class: 'viz-label', 'text-anchor': 'end' });
        el('rect', { x: lw, y, width: iw, height: bh, class: 'viz-track', rx: 3 }, g);
        el('rect', { x: lw, y, width: Math.max((r.value / max) * iw, 2), height: bh, fill: r.color, rx: 3 }, g);
        text(g, lw + (r.value / max) * iw + 6, y + bh / 2 + 4, r.display ?? r.value, { class: 'viz-value' });
        if (r.tip) bindTip(g, () => r.tip);
        if (opts.onClick) g.addEventListener('click', () => opts.onClick(r.key));
      });
    });
  }

  const ym = s => { if (!s) return null; const [y, m] = s.split('-').map(Number); return y + (m - 1) / 12; };
  const fmt = s => { const [y, m] = s.split('-').map(Number); return `${MONTHS[m - 1]} ${y}`; };

  /* Gantt chart. opts: {rows:[{label,sub,start:'YYYY-MM',end:'YYYY-MM'|null,cat,ongoing}], cats:{key:{label,color}}, from, to} */
  function gantt(container, opts) {
    responsive(container, w => {
      const narrow = w < 560;
      const lw = narrow ? 0 : 230, rh = narrow ? 40 : 30, m = { t: 6, b: 24 };
      const h = m.t + opts.rows.length * rh + m.b;
      const svg = svgRoot(container, w, h, opts.label);
      const iw = w - lw - 8, x = v => lw + ((v - opts.from) / (opts.to - opts.from)) * iw;
      for (let yr = opts.from; yr <= opts.to; yr++) {
        const major = (yr - opts.from) % (narrow ? 4 : 2) === 0;
        el('line', { x1: x(yr), x2: x(yr), y1: m.t, y2: h - m.b, class: major ? 'viz-grid' : 'viz-grid faint' }, svg);
        if (major) text(svg, x(yr), h - 7, yr, { class: 'viz-axis', 'text-anchor': 'middle' });
      }
      const now = new Date(), nowV = now.getFullYear() + now.getMonth() / 12;
      el('line', { x1: x(nowV), x2: x(nowV), y1: m.t, y2: h - m.b, class: 'viz-now' }, svg);
      opts.rows.forEach((r, i) => {
        const y = m.t + i * rh;
        const s = ym(r.start), e = r.end ? ym(r.end) + 1 / 12 : nowV, c = opts.cats[r.cat];
        const g = el('g', { class: 'viz-bar' }, svg);
        el('rect', { x: 0, y, width: w, height: rh, fill: 'transparent' }, g);
        if (!narrow) {
          text(g, 0, y + rh / 2 - 1, r.label, { class: 'viz-label strong' });
          text(g, 0, y + rh / 2 + 11, r.sub, { class: 'viz-axis' });
        }
        const by = narrow ? y + 16 : y + 7, bh = narrow ? 14 : rh - 14;
        el('rect', { x: x(s), y: by, width: Math.max(x(e) - x(s), 3), height: bh, fill: c.color, rx: 3, opacity: r.end ? 1 : 0.85 }, g);
        if (!r.end) el('rect', { x: x(e) - 3, y: by, width: 3, height: bh, fill: c.color, class: 'viz-pulse' }, g);
        if (narrow) {
          const right = x(s) > w / 2;
          text(g, right ? Math.min(x(e), w - 2) : x(s), y + 11, r.label, { class: 'viz-label strong', 'text-anchor': right ? 'end' : 'start' });
        }
        bindTip(g, () => `<b>${r.label}</b><div>${r.sub}</div><div>${fmt(r.start)} – ${r.end ? fmt(r.end) : 'Present'}</div>`);
      });
    });
  }

  /* Dot timeline: dots stacked per month (or per year with unit:'year').
     opts: {events:[{date:Date,cat,label,node}], cats, from:Date, to:Date, unit} */
  function dotTimeline(container, opts) {
    responsive(container, w => {
      const yearly = opts.unit === 'year';
      const r = yearly ? 8 : 6, m = { l: 8, r: 8, b: 22 };
      const months = yearly
        ? opts.to.getFullYear() - opts.from.getFullYear() + 1
        : (opts.to.getFullYear() - opts.from.getFullYear()) * 12 + opts.to.getMonth() - opts.from.getMonth() + 1;
      const iw = w - m.l - m.r, step = iw / months;
      const buckets = {};
      for (const ev of opts.events) {
        const k = yearly ? ev.date.getFullYear() - opts.from.getFullYear()
          : (ev.date.getFullYear() - opts.from.getFullYear()) * 12 + ev.date.getMonth() - opts.from.getMonth();
        if (k < 0 || k >= months) continue;
        (buckets[k] = buckets[k] || []).push(ev);
      }
      const maxStack = Math.max(1, ...Object.values(buckets).map(b => b.length));
      const h = maxStack * (2 * r + 3) + m.b + 10;
      const svg = svgRoot(container, w, h, opts.label);
      const base = h - m.b;
      el('line', { x1: m.l, x2: w - m.r, y1: base, y2: base, class: 'viz-baseline' }, svg);
      const labelEvery = yearly && step < 34 ? 2 : 1;
      for (let k = 0; k < months; k++) {
        const d = yearly ? new Date(opts.from.getFullYear() + k, 0, 1)
          : new Date(opts.from.getFullYear(), opts.from.getMonth() + k, 1);
        const cx = m.l + k * step + step / 2;
        if (yearly && k % labelEvery === 0) {
          text(svg, cx, h - 6, d.getFullYear(), { class: 'viz-axis', 'text-anchor': 'middle' });
        } else if (!yearly && d.getMonth() === 0) {
          el('line', { x1: m.l + k * step, x2: m.l + k * step, y1: 4, y2: base + 4, class: 'viz-grid' }, svg);
          text(svg, m.l + k * step + 3, h - 6, d.getFullYear(), { class: 'viz-axis' });
        }
        (buckets[k] || []).forEach((ev, j) => {
          const c = el('circle', { cx, cy: base - r - 2 - j * (2 * r + 3), r: Math.min(r, step / 2 - 0.5), fill: opts.cats[ev.cat].color, class: 'viz-dot' + (ev.node ? ' clickable' : '') }, svg);
          const when = yearly ? ev.date.getFullYear() : `${MONTHS[ev.date.getMonth()]} ${ev.date.getFullYear()}`;
          bindTip(c, () => `<b>${when}</b> · ${opts.cats[ev.cat].label}<div>${ev.label}</div>`);
          if (ev.node) c.addEventListener('click', () => {
            ev.node.scrollIntoView({ behavior: 'smooth', block: 'center' });
            ev.node.classList.add('flash');
            setTimeout(() => ev.node.classList.remove('flash'), 1600);
          });
        });
      }
    });
  }

  /* Heatmap. opts: {rows, cols, cells:{'row|col':{v, note}}, color} */
  function heatmap(container, opts) {
    responsive(container, w => {
      const lw = 70, ch = 30, hh = 22;
      const cw = Math.min(90, (w - lw) / opts.cols.length);
      const h = hh + opts.rows.length * ch;
      const svg = svgRoot(container, lw + cw * opts.cols.length, h, opts.label);
      opts.cols.forEach((c, j) => text(svg, lw + j * cw + cw / 2, 14, c, { class: 'viz-axis strong', 'text-anchor': 'middle' }));
      opts.rows.forEach((rw, i) => {
        const y = hh + i * ch;
        text(svg, lw - 10, y + ch / 2 + 4, rw, { class: 'viz-label strong', 'text-anchor': 'end' });
        opts.cols.forEach((c, j) => {
          const cell = opts.cells[`${rw}|${c}`];
          const g = el('g', {}, svg);
          el('rect', { x: lw + j * cw + 2, y: y + 2, width: cw - 4, height: ch - 4, rx: 4,
            fill: cell ? opts.color : 'var(--bg-alt)', opacity: cell ? (cell.v > 1 ? 1 : 0.55) : 1 }, g);
          if (cell && cell.note) text(g, lw + j * cw + cw / 2, y + ch / 2 + 4, cell.note, { 'text-anchor': 'middle', class: 'viz-cell-note' });
          if (cell) bindTip(g, () => `<b>${rw} ${c}</b><div>${cell.tip || 'Reviewer'}</div>`);
        });
      });
    });
  }

  /* Unit chart: one square per item, stacked in year columns, with an optional era band underneath.
     opts: {items:[{year,cat,flag,tip,onClick}], cats:[{key,color}], eras:[{label,from,to,color}], onYear, label} */
  function unitTimeline(container, opts) {
    responsive(container, w => {
      const ys = opts.items.map(d => d.year);
      const minY = opts.from || Math.min(...ys), maxY = opts.to || Math.max(...ys);
      const years = []; for (let y = minY; y <= maxY; y++) years.push(y);
      const step = (w - 8) / years.length;
      const perRow = step >= 60 ? 3 : step >= 18 ? 2 : 1;
      const g = step < 30 ? 1.5 : 2, s = Math.max(5.5, Math.min(15, (step - 4) / perRow - g));
      const order = Object.fromEntries(opts.cats.map((c, i) => [c.key, i]));
      const byYear = {};
      for (const d of opts.items) (byYear[d.year] = byYear[d.year] || []).push(d);
      let maxRows = 1;
      for (const y in byYear) {
        byYear[y].sort((a, b) => order[a.cat] - order[b.cat] || (b.flag ? 1 : 0) - (a.flag ? 1 : 0));
        maxRows = Math.max(maxRows, Math.ceil(byYear[y].length / perRow));
      }
      const top = 16, base = top + maxRows * (s + g), eraH = opts.eras ? 22 : 0;
      const h = base + 20 + eraH + 4;
      const svg = svgRoot(container, w, h, opts.label);
      el('line', { x1: 4, x2: w - 4, y1: base + 1, y2: base + 1, class: 'viz-baseline' }, svg);
      years.forEach((yr, i) => {
        const cx = 4 + i * step, list = byYear[yr] || [];
        const bw = perRow * (s + g) - g, x0 = cx + (step - bw) / 2;
        list.forEach((d, k) => {
          const r = Math.floor(k / perRow), c = k % perRow;
          const x = x0 + c * (s + g), y = base - (r + 1) * (s + g) + g;
          const color = (opts.cats.find(t => t.key === d.cat) || {}).color || '#94A3B8';
          const n = el('rect', { x, y, width: s, height: s, rx: Math.min(3, s / 4), fill: color,
            class: 'viz-unit' + (d.flag ? ' flag' : '') + (d.onClick ? ' clickable' : '') }, svg);
          if (d.tip) bindTip(n, d.tip);
          if (d.onClick) n.addEventListener('click', d.onClick);
        });
        if (list.length) text(svg, cx + step / 2, base - Math.ceil(list.length / perRow) * (s + g) - 3, list.length,
          { class: 'viz-axis', 'text-anchor': 'middle' });
        const every = step < 24 ? 2 : 1;
        if (i % every === 0 || i === years.length - 1) {
          const t = text(svg, cx + step / 2, base + 14, step < 34 ? `'${String(yr).slice(2)}` : yr,
            { class: 'viz-axis' + (list.length && opts.onYear ? ' clickable-year' : ''), 'text-anchor': 'middle' });
          if (list.length && opts.onYear) t.addEventListener('click', () => opts.onYear(yr));
        }
      });
      (opts.eras || []).forEach(e => {
        const x1 = 4 + (e.from - minY) * step + 1, x2 = 4 + (e.to - minY + 1) * step - 1;
        const y = base + 22;
        el('rect', { x: x1, y, width: Math.max(2, x2 - x1), height: eraH - 6, rx: 4, fill: e.color, opacity: .16 }, svg);
        el('rect', { x: x1, y, width: 3, height: eraH - 6, rx: 1.5, fill: e.color }, svg);
        const label = (x2 - x1) > e.label.length * 6.2 + 12 ? e.label : (e.short || '');
        if (label) text(svg, x1 + 8, y + 11.5, label, { class: 'viz-era' });
      });
    });
  }

  return { stackedYears, hbars, gantt, dotTimeline, heatmap, legend, unitTimeline };
})();

/* Shared category palettes */
VZ.TYPE = [
  { key: 'journal', label: 'Journal', color: '#1E40AF' },
  { key: 'conference', label: 'Conference', color: '#0891B2' },
  { key: 'workshop', label: 'Workshop / EA / Poster', color: '#7DD3E3' },
  { key: 'under-review', label: 'Under review', color: '#F59E0B' },
];
VZ.TOPIC = {
  'LLM/NLP': { label: 'LLMs / NLP', color: '#059669' },
  'Visualization': { label: 'Visualization', color: '#7C3AED' },
  'Accessibility': { label: 'Accessibility / HCI', color: '#D97706' },
  'ML': { label: 'Machine Learning', color: '#DC2626' },
  'Cloud/IoT': { label: 'Cloud / IoT', color: '#2563EB' },
};
