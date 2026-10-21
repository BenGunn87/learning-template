// Display projection only. Repository IDs and edge semantics stay unchanged.
export function prepareHierarchy(nodes, edges) {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const children = new Map(nodes.map((node) => [node.id, []]));
  const parents = new Map(nodes.map((node) => [node.id, []]));
  for (const edge of edges) {
    if (edge.type !== 'part-of') continue;
    if (!byId.has(edge.source) || !byId.has(edge.target)) continue;
    if (!children.get(edge.target).includes(edge.source)) children.get(edge.target).push(edge.source);
    if (!parents.get(edge.source).includes(edge.target)) parents.get(edge.source).push(edge.target);
  }
  const compare = (a, b) => byId.get(a).title.localeCompare(byId.get(b).title) || a.localeCompare(b);
  children.forEach((ids) => ids.sort(compare));
  parents.forEach((ids) => ids.sort(compare));
  const ids = [...byId.keys()].sort(compare);

  // Iterative Kosaraju finds source components, including cycles with no root.
  // This avoids losing a component or picking one of its downstream leaves.
  const seen = new Set();
  const order = [];
  for (const id of ids) {
    if (seen.has(id)) continue;
    const stack = [[id, false]];
    while (stack.length) {
      const [current, exiting] = stack.pop();
      if (exiting) { order.push(current); continue; }
      if (seen.has(current)) continue;
      seen.add(current);
      stack.push([current, true]);
      for (const child of [...children.get(current)].reverse()) {
        if (!seen.has(child)) stack.push([child, false]);
      }
    }
  }
  const componentOf = new Map();
  const components = [];
  for (const id of order.reverse()) {
    if (componentOf.has(id)) continue;
    const members = [];
    const stack = [id];
    const component = components.length;
    while (stack.length) {
      const current = stack.pop();
      if (componentOf.has(current)) continue;
      componentOf.set(current, component);
      members.push(current);
      stack.push(...parents.get(current));
    }
    components.push(members.sort(compare));
  }
  const hasIncoming = new Set();
  for (const id of ids) {
    for (const child of children.get(id)) {
      if (componentOf.get(id) !== componentOf.get(child)) hasIncoming.add(componentOf.get(child));
    }
  }
  const roots = components
    .filter((_, index) => !hasIncoming.has(index))
    .map((members) => ({ id: members[0], cyclic: members.length > 1 }))
    .sort((a, b) => compare(a.id, b.id));

  // One shortest display path per original Node, for search and direct URLs.
  const paths = new Map();
  const queue = roots.map(({ id }) => [id]);
  for (let index = 0; index < queue.length; index += 1) {
    const path = queue[index];
    const id = path.at(-1);
    if (paths.has(id)) continue;
    paths.set(id, path);
    for (const child of children.get(id)) {
      if (!paths.has(child)) queue.push([...path, child]);
    }
  }
  return { byId, children, parents, roots, paths };
}

export const occurrenceId = (path) => path.join('/');
const edgeLabels = { prerequisite: 'предпосылка', related: 'связь' };

export function projectHierarchy(hierarchy, expanded, selectedId, callbacks, extraEdges) {
  const nodes = [];
  const edges = [];
  const occurrences = new Map();
  let row = 0;
  // Explicit traversal also handles deep graphs without using the JS call stack.
  for (const root of hierarchy.roots) {
    const stack = [{ path: [root.id], parent: null, exiting: false }];
    const positioned = new Map();
    while (stack.length) {
      const item = stack.pop();
      const id = occurrenceId(item.path);
      const originalId = item.path.at(-1);
      const cycle = item.path.slice(0, -1).includes(originalId);
      const childIds = hierarchy.children.get(originalId);
      const open = !cycle && expanded.has(id) && childIds.length > 0;
      if (!item.exiting && open) {
        stack.push({ ...item, exiting: true });
        for (const child of [...childIds].reverse()) {
          stack.push({ path: [...item.path, child], parent: id, exiting: false });
        }
        continue;
      }
      let y;
      if (open) {
        const positions = childIds.map((child) => positioned.get(`${id}/${child}`));
        y = (positions[0] + positions.at(-1)) / 2;
      } else {
        y = row++ * 132;
      }
      positioned.set(id, y);
      const node = hierarchy.byId.get(originalId);
      nodes.push({
        id, type: 'knowledge', position: { x: (item.path.length - 1) * 330, y },
        selected: originalId === selectedId,
        data: {
          ...node, originalId, cycle, open, childCount: childIds.length,
          parentCount: hierarchy.parents.get(originalId).length,
          rootless: item.path.length === 1 && root.cyclic,
          onToggle: () => callbacks.onToggle(id),
          onSelect: () => callbacks.onSelect(originalId, cycle ? null : id),
        },
      });
      if (!cycle) {
        if (!occurrences.has(originalId)) occurrences.set(originalId, []);
        occurrences.get(originalId).push(id);
      }
      if (item.parent) edges.push({
        id: `part-of:${id}`, source: id, target: item.parent, type: 'smoothstep',
        markerEnd: { type: 'arrowclosed', width: 12, height: 12 },
        style: { stroke: cycle ? '#d18c45' : '#a4b7ad', strokeDasharray: cycle ? '5 5' : undefined },
      });
    }
    // Extra space separates expanded trees; collapsed roots stay compact.
    if (expanded.has(root.id) && hierarchy.children.get(root.id).length) row += 0.6;
  }

  // Non-hierarchical edges connect one visible occurrence of each endpoint.
  // Never connect hidden nodes to their ancestors, which would invent a new
  // relationship.
  for (const [index, edge] of extraEdges.entries()) {
    const source = occurrences.get(edge.source)?.[0];
    const target = occurrences.get(edge.target)?.[0];
    if (!source || !target) continue;
    edges.push({
      id: `${edge.type}:${index}`, source, target, type: 'default',
      label: edgeLabels[edge.type] || edge.type, animated: false,
      markerEnd: edge.type === 'prerequisite' ? { type: 'arrowclosed' } : undefined,
      style: { stroke: edge.type === 'prerequisite' ? '#af7740' : '#7b80a3', strokeDasharray: '5 5' },
      labelStyle: { fontSize: 10, fill: '#5c6470' },
    });
  }
  return { nodes, edges };
}
