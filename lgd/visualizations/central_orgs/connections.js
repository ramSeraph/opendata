/* Shared connector trunks and indexed viewport queries; source edges stay intact. */
(function (global) {
  'use strict';

  class IntervalIndex {
    constructor(groups) {
      this.rows = groups.sort((a, b) => a.ymin - b.ymin);
      this.size = 1;
      while (this.size < groups.length) this.size *= 2;
      this.max = new Float64Array(this.size * 2).fill(-Infinity);
      groups.forEach((g, i) => { this.max[this.size + i] = g.ymax; });
      for (let i = this.size - 1; i; i--) this.max[i] = Math.max(this.max[i * 2], this.max[i * 2 + 1]);
    }
    between(ymin, ymax) {
      const found = [], stack = [[1, 0, this.size]];
      while (stack.length) {
        const [node, lo, hi] = stack.pop();
        if (lo >= this.rows.length || this.max[node] < ymin || this.rows[lo].ymin > ymax) continue;
        if (hi - lo === 1) found.push(this.rows[lo]);
        else {
          const mid = (lo + hi) >>> 1;
          stack.push([node * 2 + 1, mid, hi], [node * 2, lo, mid]);
        }
      }
      return found;
    }
  }

  class ConnectionIndex {
    constructor(edges, nodes, cardWidth, cardHeight) {
      const groups = new Map(), columns = new Map();
      for (const edge of edges) {
        const a = nodes.get(edge.source), b = nodes.get(edge.target);
        const style = edge.association_id ? 'title' : /membership|title|designation/.test(edge.label) ? 'association' : 'parent';
        const key = JSON.stringify([edge.source, b.x, style, edge.label]);
        if (!groups.has(key)) {
          const ax = a.x + cardWidth, bx = b.x;
          // Separate connector styles from the same parent within the column gap.
          const mx = (ax + bx) / 2 + (style === 'title' ? -8 : style === 'parent' ? 8 : 0);
          groups.set(key, {ax, ay: a.y + cardHeight / 2, bx, mx, style, targets: []});
        }
        groups.get(key).targets.push({edge, y: b.y + cardHeight / 2});
      }
      for (const group of groups.values()) {
        group.targets.sort((a, b) => a.y - b.y);
        group.ymin = Math.min(group.ay, group.targets[0].y);
        group.ymax = Math.max(group.ay, group.targets.at(-1).y);
        const key = JSON.stringify([group.ax, group.bx]);
        if (!columns.has(key)) columns.set(key, {xmin: group.ax, xmax: group.bx, groups: []});
        columns.get(key).groups.push(group);
      }
      this.columns = [...columns.values()].map(({groups, ...column}) => ({...column, index: new IntervalIndex(groups)}));
    }
    query({xmin, xmax, ymin, ymax}) {
      const segments = [], branches = [];
      let groupsVisited = 0, targetsVisited = 0;
      const horizontal = (x1, x2, y, style) => {
        if (y < ymin || y > ymax || x2 < xmin || x1 > xmax) return;
        segments.push({x1: Math.max(xmin, x1), y1: y, x2: Math.min(xmax, x2), y2: y, style});
      };
      for (const column of this.columns) {
        if (column.xmax < xmin || column.xmin > xmax) continue;
        for (const g of column.index.between(ymin, ymax)) {
          groupsVisited++;
          horizontal(g.ax, g.mx, g.ay, g.style);
          if (g.mx >= xmin && g.mx <= xmax && g.ymax > g.ymin) {
            segments.push({x1: g.mx, y1: Math.max(ymin, g.ymin), x2: g.mx, y2: Math.min(ymax, g.ymax), style: g.style});
          }
          if (g.bx < xmin || g.mx > xmax) continue;
          let lo = 0, hi = g.targets.length;
          while (lo < hi) {
            const mid = (lo + hi) >>> 1;
            if (g.targets[mid].y < ymin) lo = mid + 1;
            else hi = mid;
          }
          for (let i = lo; i < g.targets.length && g.targets[i].y <= ymax; i++) {
            targetsVisited++;
            const {edge, y} = g.targets[i];
            horizontal(g.mx, g.bx, y, g.style);
            branches.push({edge, x: g.bx, y, labelX: (g.ax + g.bx) / 2, style: g.style});
          }
        }
      }
      return {segments, branches, groupsVisited, targetsVisited};
    }
  }

  const api = {ConnectionIndex};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.LGDConnections = api;
})(globalThis);
