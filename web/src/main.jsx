import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, useLocation, useNavigate } from 'react-router-dom';
import { Background, Controls, Handle, Position, ReactFlow, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { occurrenceId, prepareHierarchy, projectHierarchy } from './hierarchy';
import './style.css';

const typeLabels = { area: 'Область', topic: 'Тема', concept: 'Понятие' };
const dimensions = { recall: 'Recall', understanding: 'Understanding', application: 'Application' };
const statuses = { learning: 'Изучение', practice: 'Практика', verified: 'Проверено' };
const grades = { failed: 'Не получилось', hard: 'Сложно', good: 'Хорошо', easy: 'Легко' };

function useResource(path) {
  const [state, setState] = useState({ path, loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ path, loading: true });
    fetch(path, { signal: controller.signal, cache: 'no-store' })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || `Ошибка ${response.status}`);
        return body;
      })
      .then((data) => setState({ path, data, loading: false }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ path, error: error.message, loading: false });
      });
    return () => controller.abort();
  }, [path]);
  return state.path === path ? state : { loading: true };
}

function Warnings({ warnings = [] }) {
  if (!warnings.length) return null;
  return <details className="warnings"><summary>Есть неполные данные · {warnings.length}</summary>
    <ul>{warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
  </details>;
}

function Message({ title, children, error = false }) {
  return <div className={`message ${error ? 'error' : ''}`} role={error ? 'alert' : 'status'}>
    <span className="message-icon">{error ? '!' : '◇'}</span><h2>{title}</h2><p>{children}</p>
  </div>;
}

function ProgressBadge({ unit }) {
  if (unit.kind === 'planned') return <span className="badge planned">Planned</span>;
  if (!unit.progress) return <span className="badge">Нет Progress</span>;
  return <span className={`badge ${unit.progress.status}`}>{statuses[unit.progress.status]}</span>;
}

function Gaps({ gaps }) {
  if (!gaps.length) return <p className="muted">Активных Gaps нет.</p>;
  return <div className="gap-list">{gaps.map((gap) => <div className="gap-card" key={gap.id}>
    <div><strong>{dimensions[gap.dimension]}</strong><span className="badge gap">{gap.status}</span></div>
    <Link to={`/nodes/${gap.node}`}>{gap.node}</Link>
    <small>{gap.routing_impact} · {gap.scope}</small>
  </div>)}</div>;
}

function NodeLinks({ nodes, empty = 'Нет связей.' }) {
  return nodes.length ? <div className="node-links">{nodes.map((node) =>
    <Link key={node.id} to={`/nodes/${node.id}`}><span className={`dot ${node.type}`} />{node.title}<span>↗</span></Link>)}</div>
    : <p className="muted">{empty}</p>;
}

function UnitList({ units }) {
  if (!units.length) return <p className="muted">Нет связанных Units.</p>;
  return <div className="unit-list">{units.map((unit) => <Link className="unit-card" key={unit.id} to={`/units/${unit.id}`}>
    <div><ProgressBadge unit={unit} /><span aria-hidden="true">↗</span></div>
    <strong>{unit.title}</strong>
    {unit.kind === 'initialized' && unit.in_frontier && <small>Также во Frontier</small>}
  </Link>)}</div>;
}

function NodePanel({ id, hierarchy, occurrence }) {
  const { data, error, loading } = useResource(`/api/nodes/${encodeURIComponent(id)}`);
  if (loading) return <aside className="inspector"><Message title="Загрузка узла…" /></aside>;
  if (error) return <aside className="inspector"><Link to="/" className="close">Закрыть ×</Link><Message error title="Не удалось открыть узел">{error}</Message></aside>;
  const { node, parents, children, edges, related_nodes, units, gaps } = data;
  const path = occurrence?.split('/') || hierarchy.paths.get(id) || [id];
  return <aside className="inspector" aria-label="Выбранный Node" key={id}>
    <div className="panel-heading"><span className="eyebrow">ДЕТАЛИ УЗЛА</span><Link to="/" className="close" aria-label="Закрыть панель">×</Link></div>
    <span className={`badge type-${node.type}`}>{typeLabels[node.type]}</span>
    <h2>{node.title}</h2><code className="record-id">{node.id}</code>
    {node.status === 'deprecated' && <span className="badge">Устаревший Node</span>}
    <p className="description">{node.summary || 'Описание пока не добавлено.'}</p>
    <section><h3>Место на карте</h3><div className="breadcrumbs">{path.map((key, index) => <React.Fragment key={key}>
      {index > 0 && <span> / </span>}<Link to={`/nodes/${key}`}>{hierarchy.byId.get(key)?.title || key}</Link>
    </React.Fragment>)}</div>
      <h4>Родители{parents.length > 1 ? ' · несколько представлений на карте' : ''}</h4>
      <NodeLinks nodes={parents} empty="Нет родителей. Узел находится в корне или в циклической компоненте без корня." />
      <h4>Дочерние узлы</h4><NodeLinks nodes={children} />
    </section>
    <section><h3>Учебные Units <span>{units.filter((unit) => unit.kind === 'initialized').length}</span></h3>
      <UnitList units={units.filter((unit) => unit.kind === 'initialized')} />
      <h3>Запланированные Units <span>{units.filter((unit) => unit.kind === 'planned').length}</span></h3>
      <UnitList units={units.filter((unit) => unit.kind === 'planned')} />
    </section>
    <section><h3>Активные Gaps <span>{gaps.length}</span></h3><Gaps gaps={gaps} /></section>
    <section><h3>Все прямые связи</h3>{edges.length ? <ul className="relation-list">{edges.map((edge, index) => {
      const otherId = edge.source === id ? edge.target : edge.source;
      const other = related_nodes.find((item) => item.id === otherId);
      return <li key={index}><small>{edge.type} · {edge.source === id ? '→' : '←'}</small><Link to={`/nodes/${otherId}`}>{other?.title || otherId}</Link></li>;
    })}</ul> : <p className="muted">Нет связей.</p>}</section>
    <p className="footnote">Units и Gaps относятся только к этому узлу.</p>
    <Warnings warnings={data.warnings} />
  </aside>;
}

function UnitPage({ id }) {
  const { data, error, loading } = useResource(`/api/units/${encodeURIComponent(id)}`);
  if (loading) return <Message title="Загрузка Unit…" />;
  if (error) return <div className="unit-page"><Link to="/">← К карте знаний</Link><Message error title="Не удалось открыть Unit">{error}</Message></div>;
  const { unit, nodes, gaps } = data;
  return <article className="unit-page">
    <Link to="/" className="back-link">← Карта знаний</Link>
    <div className="unit-heading"><span className="eyebrow">{unit.kind === 'planned' ? 'ЗАПЛАНИРОВАННАЯ UNIT' : 'УЧЕБНАЯ UNIT'}</span><ProgressBadge unit={unit} /></div>
    <h1>{unit.title}</h1><code className="record-id">{unit.id}</code>
    <p className="unit-goal">{unit.goal || 'Описание пока не добавлено.'}</p>
    {unit.kind === 'initialized' && unit.in_frontier && <p className="muted">Эта Unit также присутствует во Frontier.</p>}
    <section><h2>Текущий Progress</h2>
      {unit.progress ? <><p className="muted">Последние сохранённые результаты Unit</p><div className="grade-grid">{Object.entries(dimensions).map(([key, label]) =>
        <div className="grade-card" key={key}><span>{label}</span><strong>{grades[unit.progress.mastery[key]] || 'Нет данных'}</strong></div>)}</div></>
        : <p className="muted">{unit.kind === 'planned' ? 'Unit пока только запланирована. Progress отсутствует.' : 'Для этой Unit ещё нет сохранённого Progress.'}</p>}
    </section>
    <div className="unit-columns"><section><h2>Связанные Nodes</h2><NodeLinks nodes={nodes} /></section>
      <section><h2>Активные Gaps <span className="count">{gaps.length}</span></h2><Gaps gaps={gaps} /></section></div>
    <Warnings warnings={data.warnings} />
  </article>;
}

function KnowledgeNode({ data, selected }) {
  return <div className={`knowledge-node ${data.type} ${selected ? 'chosen' : ''} ${data.cycle ? 'cyclic' : ''}`}>
    <Handle type="source" position={Position.Left} />
    <button className="node-body nodrag" onClick={data.onSelect} aria-label={`Открыть ${data.title}`}>
      <span className="node-type">{typeLabels[data.type]}{data.multipleParents && ' · ↗'}{data.rootless && ' · без корня'}</span>
      <strong>{data.title}</strong>
      {data.cycle && <small>↩ Циклическая связь · перейти к узлу</small>}
    </button>
    {!data.cycle && data.childCount > 0 && <button className="expand-node nodrag" onClick={data.onToggle}
      aria-label={`${data.open ? 'Свернуть' : 'Раскрыть'} ${data.title}`} aria-expanded={data.open}>
      <span>{data.open ? '−' : '+'}</span><small>{data.childCount}</small>
    </button>}
    <Handle type="target" position={Position.Right} />
  </div>;
}

const nodeTypes = { knowledge: KnowledgeNode };

function MapCanvas({ hierarchy, map, selectedId, onSelect, expanded, setExpanded, focus }) {
  const [links, setLinks] = useState({ prerequisite: false, related: false });
  const { setCenter } = useReactFlow();
  const onToggle = useCallback((id) => setExpanded((previous) => {
    const next = new Set(previous);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  }), [setExpanded]);
  const projection = useMemo(() => projectHierarchy(hierarchy, expanded, selectedId,
    { onSelect, onToggle }, map.edges.filter((edge) => links[edge.type])),
  [hierarchy, expanded, selectedId, onSelect, onToggle, map.edges, links]);
  useEffect(() => {
    if (!focus?.id) return;
    const target = projection.nodes.find((node) => node.id === focus.id);
    if (!target) return;
    const timer = setTimeout(() => setCenter(target.position.x + 130, target.position.y + 45, { zoom: 0.95, duration: 350 }), 60);
    return () => clearTimeout(timer);
  }, [focus, projection.nodes, setCenter]);
  return <div className="map-canvas">
    <div className="map-toolbar"><div><span className="eyebrow">СВЯЗИ НА КАРТЕ</span><span className="hierarchy-key">● part-of</span></div>
      {['prerequisite', 'related'].map((type) => <label key={type}><input type="checkbox" checked={links[type]} onChange={(event) => setLinks({ ...links, [type]: event.target.checked })} />{type}</label>)}
    </div>
    <ReactFlow nodes={projection.nodes} edges={projection.edges} nodeTypes={nodeTypes}
      nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}
      fitView fitViewOptions={{ padding: 0.22, maxZoom: 1 }} minZoom={0.15} maxZoom={1.7}
      ariaLabelConfig={{ 'controls.zoomIn.ariaLabel': 'Приблизить', 'controls.zoomOut.ariaLabel': 'Отдалить', 'controls.fitView.ariaLabel': 'Показать всю карту' }}>
      <Background color="#d4d9d1" gap={22} size={1} /><Controls showInteractive={false} />
    </ReactFlow>
    <div className="map-legend"><span><i className="dot area" />Область</span><span><i className="dot topic" />Тема</span><span><i className="dot concept" />Понятие</span></div>
    <p className="map-hint">+/− раскрывают ветви · прокрутка меняет масштаб</p>
  </div>;
}

function App() {
  const { data: map, loading, error } = useResource('/api/map');
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState(new Set());
  const [focus, setFocus] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();
  const match = location.pathname.match(/^\/(nodes|units)\/([a-z0-9]+(?:-[a-z0-9]+)*)\/?$/);
  const selectedId = match?.[1] === 'nodes' ? match[2] : null;
  const unitId = match?.[1] === 'units' ? match[2] : null;
  const unknownRoute = location.pathname !== '/' && !match;
  const hierarchy = useMemo(() => prepareHierarchy(map?.nodes || [], map?.edges || []), [map]);
  useEffect(() => { setExpanded(new Set(hierarchy.roots.map(({ id }) => id))); }, [hierarchy]);

  const reveal = useCallback((id, preferredOccurrence = null) => {
    const path = preferredOccurrence?.split('/') || hierarchy.paths.get(id);
    if (!path) return;
    setExpanded((previous) => {
      const next = new Set(previous);
      for (let index = 1; index < path.length; index += 1) next.add(occurrenceId(path.slice(0, index)));
      return next;
    });
    setFocus({ id: occurrenceId(path), nonce: Date.now() });
  }, [hierarchy]);

  // Search, browser navigation, direct URLs, and links from Unit pages all open
  // ancestor occurrences. Clicking a visible duplicate preserves its branch.
  useEffect(() => {
    if (selectedId) reveal(selectedId, location.state?.occurrence);
  }, [selectedId, hierarchy, reveal, location.key, location.state]);
  const selectNode = useCallback((id, occurrence = null) => {
    setQuery('');
    navigate(`/nodes/${id}`, { state: { occurrence } });
  }, [navigate]);

  const searchResults = query.trim() ? [...hierarchy.byId.values()]
    .filter((node) => node.title.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())) : [];

  return <div className="app-shell">
    <aside className="sidebar">
      <Link className="brand" to="/"><span className="brand-mark">⌘</span><span>Learning<small>ЛИЧНАЯ БАЗА ЗНАНИЙ</small></span></Link>
      <div className="sidebar-section"><span className="eyebrow">ПРОСТРАНСТВО ОБУЧЕНИЯ</span>
        <Link className="nav-current" to="/"><span>⌘</span>Карта знаний<span>↗</span></Link>
      </div>
      <div className="sidebar-section search-section"><label className="eyebrow" htmlFor="node-search">НАЙТИ НА КАРТЕ</label>
        <div className="search-box"><span aria-hidden="true">⌕</span><input id="node-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Название узла…" autoComplete="off" /></div>
        {query.trim() && <div className="search-results" aria-live="polite"><small>Найдено: {searchResults.length}</small>
          {searchResults.map((node) => <button key={node.id} onClick={() => selectNode(node.id)}><span className={`dot ${node.type}`} /><span>{node.title}<small>{typeLabels[node.type]}</small></span><span>↗</span></button>)}
          {!searchResults.length && <p className="muted">Совпадений нет.</p>}
        </div>}
      </div>
      <div className="sidebar-section roots-nav"><span className="eyebrow">НАЧАЛО КАРТЫ</span>
        {hierarchy.roots.map((root) => <button key={root.id} onClick={() => selectNode(root.id)}><span className={`dot ${hierarchy.byId.get(root.id).type}`} />{hierarchy.byId.get(root.id).title}{root.cyclic && <small>↩</small>}</button>)}
      </div>
      <div className="sidebar-footer"><span className={`mode-dot ${map?.mode === 'demo' ? 'demo' : ''}`} /><div>{map?.mode === 'demo' ? 'Демонстрационный режим' : 'Локальный репозиторий'}<small>Только чтение · без синхронизации</small></div></div>
    </aside>
    <div className="workspace">
      <header className="workspace-header"><div><div className="eyebrow">{unitId ? 'УЧЕБНЫЙ МАТЕРИАЛ' : 'ВАШЕ ПРОСТРАНСТВО ЗНАНИЙ'}</div><h1>{unitId ? 'Unit' : 'Карта знаний'}</h1></div>
        <div className="header-meta">{map?.mode === 'demo' && <span className="badge demo-badge">DEMO</span>}<span className="readonly">◉ Только чтение</span></div>
      </header>
      {map && <Warnings warnings={map.warnings} />}
      {loading ? <Message title="Загрузка карты…" /> : error ? <Message error title="Карта недоступна">{error}</Message>
        : unknownRoute ? <Message error title="Страница не найдена"><Link to="/">Открыть карту знаний</Link></Message>
        : unitId ? <UnitPage id={unitId} />
        : map.repository_state === 'uninitialized' ? <Message title="Тема ещё не инициализирована">В этом репозитории пока нет карты знаний. Начните обучение через агента или запустите интерфейс с флагом --demo для знакомства.</Message>
        : !map.nodes.length ? <Message title="Карта пока пуста">В репозитории нет доступных Graph Nodes.</Message>
        : <><div className="map-subheader"><span>Все знания <span className="slash">/</span> <strong>{selectedId ? hierarchy.byId.get(selectedId)?.title || selectedId : 'Обзор'}</strong></span><span>{map.nodes.length} узлов · {map.edges.length} связей</span></div>
          <div className="map-workspace"><ReactFlowProvider><MapCanvas hierarchy={hierarchy} map={map} selectedId={selectedId} expanded={expanded} setExpanded={setExpanded} focus={focus} onSelect={selectNode} /></ReactFlowProvider>
            {selectedId && <NodePanel id={selectedId} hierarchy={hierarchy} occurrence={location.state?.occurrence} />}
          </div></>}
    </div>
  </div>;
}

createRoot(document.getElementById('root')).render(<BrowserRouter><App /></BrowserRouter>);
