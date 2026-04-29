// D3-based Gantt renderer with drag (move + resize) and dependency arrows.
const Gantt = (() => {
  const ROW_H = 36;
  const HEADER_H = 40;
  const NAME_W_MIN = 120;
  const NAME_W_MAX = 420;
  const NAME_PAD = 24; // total horizontal padding inside name column
  const PADDING = 4;
  const RESIZE_HANDLE = 8;

  let NAME_W = 180;     // computed per render
  let cellW = 40;       // px per unit (day or week)
  let onTaskUpdate = null;
  let onTaskClick = null;
  let labelMode = 'name'; // 'name' | 'duration' | 'none'
  let buffer = 4;       // extra units after last task

  function unitsToDate(schedule, units) {
    const start = new Date(schedule.start_date + 'T00:00:00');
    const ms = (schedule.mode === 'week' ? 7 : 1) * units * 86400000;
    return new Date(start.getTime() + ms);
  }

  function maxEnd(tasks) {
    return tasks.reduce((m, t) => Math.max(m, t.start_offset + t.duration), 0);
  }

  function measureNameWidth(tasks) {
    if (!tasks.length) return NAME_W_MIN;
    // Reuse a single canvas for measurement.
    const c = measureNameWidth._c || (measureNameWidth._c = document.createElement('canvas'));
    const ctx = c.getContext('2d');
    ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    let max = 0;
    for (const t of tasks) {
      const w = ctx.measureText(t.name || '').width;
      if (w > max) max = w;
    }
    return Math.min(NAME_W_MAX, Math.max(NAME_W_MIN, Math.ceil(max + NAME_PAD)));
  }

  function configure(opts) {
    onTaskUpdate = opts.onTaskUpdate || null;
    onTaskClick = opts.onTaskClick || null;
    if (typeof opts.labelMode === 'string') labelMode = opts.labelMode;
    if (typeof opts.buffer === 'number' && !isNaN(opts.buffer)) {
      buffer = Math.max(0, Math.floor(opts.buffer));
    }
  }

  function labelFor(d, schedule) {
    if (labelMode === 'none') return '';
    if (labelMode === 'duration') {
      const unit = schedule.mode === 'week' ? 'wk' : 'd';
      return `${d.duration}${unit}`;
    }
    return d.name;
  }

  function render(container, schedule, tasks) {
    const root = d3.select(container);
    root.selectAll('*').remove();

    NAME_W = measureNameWidth(tasks);

    const totalUnits = Math.max(maxEnd(tasks) + buffer, Math.max(buffer, 1));
    // Default cell widths
    const defaultCell = schedule.mode === 'week' ? 60 : 36;
    // Fill the container if there's room; otherwise use the default and scroll.
    const availW = (container.clientWidth || 800) - NAME_W - 2;
    const fitCell = availW / totalUnits;
    cellW = Math.max(defaultCell, fitCell);
    const chartW = totalUnits * cellW;
    const chartH = Math.max(tasks.length, 1) * ROW_H;
    const svgW = NAME_W + chartW;
    const svgH = HEADER_H + chartH + 20;

    const svg = root.append('svg')
      .attr('class', 'gantt-svg')
      .attr('width', svgW)
      .attr('height', svgH);

    // arrow marker
    const defs = svg.append('defs');
    defs.append('marker')
      .attr('id', 'arrow-head')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 8)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'var(--lam-warn)');

    // Row backgrounds (left name area + chart)
    const rowsG = svg.append('g').attr('transform', `translate(0,${HEADER_H})`);
    rowsG.selectAll('rect.gantt-row-bg')
      .data(tasks)
      .enter()
      .append('rect')
      .attr('class', 'gantt-row-bg')
      .attr('x', 0)
      .attr('y', (_, i) => i * ROW_H)
      .attr('width', svgW)
      .attr('height', ROW_H);

    // Task names column
    const namesG = svg.append('g').attr('transform', `translate(8,${HEADER_H})`);
    namesG.selectAll('text.row-name')
      .data(tasks)
      .enter()
      .append('text')
      .attr('class', 'row-name')
      .attr('x', 4)
      .attr('y', (_, i) => i * ROW_H + ROW_H / 2 + 4)
      .text((d) => d.name);

    // Vertical separator
    svg.append('line')
      .attr('x1', NAME_W).attr('x2', NAME_W)
      .attr('y1', 0).attr('y2', svgH)
      .attr('stroke', 'var(--lam-light-gray)');

    // Header (timeline axis)
    const headerG = svg.append('g').attr('transform', `translate(${NAME_W},0)`);
    headerG.append('rect')
      .attr('x', 0).attr('y', 0)
      .attr('width', chartW).attr('height', HEADER_H)
      .attr('fill', 'var(--lam-bg)');

    const ticks = d3.range(0, totalUnits + 1);
    const fmtDay = d3.timeFormat('%b %d');
    const fmtWeek = (d) => `W${d3.timeFormat('%V')(d)}`;

    // Return the Monday on/before the given date.
    const mondayOf = (d) => {
      const x = new Date(d.getTime());
      // getDay(): Sun=0, Mon=1, ..., Sat=6  -> shift so Monday is the anchor.
      const dow = (x.getDay() + 6) % 7; // Mon=0 ... Sun=6
      x.setDate(x.getDate() - dow);
      return x;
    };

    headerG.selectAll('text.tick-label')
      .data(ticks)
      .enter()
      .append('text')
      .attr('class', 'tick-label')
      .attr('x', (u) => u * cellW + 4)
      .attr('y', 16)
      .attr('font-size', 11)
      .attr('fill', 'var(--lam-gray)')
      .text((u) => {
        const d = unitsToDate(schedule, u);
        return schedule.mode === 'week' ? fmtWeek(mondayOf(d)) : fmtDay(d);
      });

    headerG.selectAll('text.tick-sub')
      .data(ticks)
      .enter()
      .append('text')
      .attr('class', 'tick-sub')
      .attr('x', (u) => u * cellW + 4)
      .attr('y', 32)
      .attr('font-size', 10)
      .attr('fill', 'var(--lam-gray)')
      .text((u) => {
        const d = unitsToDate(schedule, u);
        return schedule.mode === 'week'
          ? d3.timeFormat('%b %d')(mondayOf(d))
          : d3.timeFormat('%a')(d);
      });

    // Grid lines
    const gridG = svg.append('g')
      .attr('class', 'gantt-grid')
      .attr('transform', `translate(${NAME_W},${HEADER_H})`);
    gridG.selectAll('line')
      .data(ticks)
      .enter()
      .append('line')
      .attr('x1', (u) => u * cellW)
      .attr('x2', (u) => u * cellW)
      .attr('y1', 0)
      .attr('y2', chartH);

    // Tasks layer
    const chartG = svg.append('g').attr('transform', `translate(${NAME_W},${HEADER_H})`);

    // Dependencies (drawn under bars)
    const depG = chartG.append('g').attr('class', 'dep-layer');
    const taskMap = new Map(tasks.map((t, i) => [t.id, { task: t, index: i }]));
    tasks.forEach((t) => {
      (t.dependencies || []).forEach((dep) => {
        const from = taskMap.get(dep.prerequisite_id);
        const to = taskMap.get(t.id);
        if (!from || !to) return;
        const fx = (from.task.start_offset + from.task.duration) * cellW;
        const fy = from.index * ROW_H + ROW_H / 2;
        const tx = to.task.start_offset * cellW;
        const ty = to.index * ROW_H + ROW_H / 2;
        const midX = (fx + tx) / 2;
        depG.append('path')
          .attr('class', 'dep-arrow')
          .attr('d', `M${fx},${fy} C${midX},${fy} ${midX},${ty} ${tx},${ty}`);
      });
    });

    // Bars
    const barsG = chartG.append('g').attr('class', 'bars-layer');
    const groups = barsG.selectAll('g.task-group')
      .data(tasks, (d) => d.id)
      .enter()
      .append('g')
      .attr('class', 'task-group')
      .attr('transform', (_, i) => `translate(0,${i * ROW_H + PADDING})`);

    const barH = ROW_H - 2 * PADDING;

    groups.append('rect')
      .attr('class', 'task-bar')
      .attr('x', (d) => d.start_offset * cellW)
      .attr('y', 0)
      .attr('width', (d) => d.duration * cellW)
      .attr('height', barH)
      .on('click', (event, d) => {
        if (event.defaultPrevented) return;
        if (onTaskClick) onTaskClick(d);
      });

    groups.append('rect')
      .attr('class', 'task-progress')
      .attr('x', (d) => d.start_offset * cellW)
      .attr('y', 0)
      .attr('width', (d) => d.duration * cellW * (d.progress || 0))
      .attr('height', barH);

    groups.append('text')
      .attr('class', 'task-label')
      .attr('x', (d) => d.start_offset * cellW + 8)
      .attr('y', barH / 2 + 4)
      .attr('display', labelMode === 'none' ? 'none' : null)
      .text((d) => labelFor(d, schedule));

    // Resize handle
    groups.append('rect')
      .attr('class', 'task-resize')
      .attr('x', (d) => (d.start_offset + d.duration) * cellW - RESIZE_HANDLE)
      .attr('y', 0)
      .attr('width', RESIZE_HANDLE)
      .attr('height', barH);

    // Drag for move
    groups.select('rect.task-bar').call(
      d3.drag()
        .on('start', function () {
          d3.select(this).classed('dragging', true);
        })
        .on('drag', function (event, d) {
          d._dragX = (d._dragX ?? d.start_offset * cellW) + event.dx;
          const snap = Math.max(0, Math.round(d._dragX / cellW));
          d.start_offset = snap;
          updateGroupPositions(d3.select(this.parentNode), d, barH, schedule);
        })
        .on('end', function (event, d) {
          d3.select(this).classed('dragging', false);
          delete d._dragX;
          if (onTaskUpdate) onTaskUpdate(d, { start_offset: d.start_offset });
        })
    );

    // Drag for resize
    groups.select('rect.task-resize').call(
      d3.drag()
        .on('drag', function (event, d) {
          d._dragW = (d._dragW ?? d.duration * cellW) + event.dx;
          const snap = Math.max(1, Math.round(d._dragW / cellW));
          d.duration = snap;
          updateGroupPositions(d3.select(this.parentNode), d, barH, schedule);
        })
        .on('end', function (event, d) {
          delete d._dragW;
          if (onTaskUpdate) onTaskUpdate(d, { duration: d.duration });
        })
    );
  }

  function updateGroupPositions(group, d, barH, schedule) {
    group.select('rect.task-bar')
      .attr('x', d.start_offset * cellW)
      .attr('width', d.duration * cellW);
    group.select('rect.task-progress')
      .attr('x', d.start_offset * cellW)
      .attr('width', d.duration * cellW * (d.progress || 0));
    group.select('text.task-label')
      .attr('x', d.start_offset * cellW + 8)
      .text(schedule ? labelFor(d, schedule) : d.name);
    group.select('rect.task-resize')
      .attr('x', (d.start_offset + d.duration) * cellW - RESIZE_HANDLE);
  }

  return { configure, render };
})();
