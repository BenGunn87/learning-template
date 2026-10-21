import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, useLocation, useNavigate } from 'react-router-dom';
import { Background, Controls, Handle, Position, ReactFlow, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { occurrenceId, prepareHierarchy, projectHierarchy } from './hierarchy';
import './style.css';

const typeLabels = { area: 'Область', topic: 'Тема', concept: 'Понятие' };
const dimensions = { recall: 'Запоминание', understanding: 'Понимание', application: 'Применение' };
const statuses = { learning: 'Изучение', practice: 'Практика', verified: 'Проверено' };
const grades = { failed: 'Не получилось', hard: 'Сложно', good: 'Хорошо', easy: 'Легко' };
const gapStatuses = { detected: 'Обнаружен', confirmed: 'Подтверждён' };
const impacts = { blocking: 'Блокирующий', important: 'Важный', minor: 'Незначительный' };
const scopes = { local: 'локальный', 'cross-concept': 'между понятиями' };
const linkLabels = { prerequisite: 'Предпосылки', related: 'Связанные' };
// Graph edges point from → to; prerequisite means "from is needed for to".
const relationLabels = {
  'part-of': { out: 'Входит в', in: 'Содержит' },
  prerequisite: { out: 'Нужен для', in: 'Требует' },
  related: { out: 'Связан с', in: 'Связан с' },
};
const MOBILE = '(max-width: 720px)';

function plural(count, [one, few, many]) {
  const tens = count % 100;
  const units = count % 10;
  if (tens >= 11 && tens <= 14) return many;
  if (units === 1) return one;
  if (units >= 2 && units <= 4) return few;
  return many;
}

const formatDate = (value) => value ? new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) : null;

// Keeps the previous response visible while the next one loads, so panels do
// not flash to an empty loading state on every selection.
function useResource(path) {
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ data: previous.data, loading: true }));
    fetch(path, { signal: controller.signal, cache: 'no-store' })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || `Ошибка ${response.status}`);
        return body;
      })
      .then((data) => setState({ data, loading: false }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ error: error.message, loading: false });
      });
    return () => controller.abort();
  }, [path]);
  return state;
}

function Warnings({ warnings = [] }) {
  if (!warnings.length) return null;
  return <details className="warnings"><summary>Есть неполные данные · {warnings.length}</summary>
    <ul>{warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
  </details>;
}

function Message({ title, children, error = false }) {
  return <div className={`message ${error ? 'error' : ''}`} role={error ? 'alert' : 'status'}>
    <span className="message-icon">{error ? '!' : '◇'}</span><h2>{title}</h2>{children && <p>{children}</p>}
  </div>;
}

function ProgressBadge({ unit }) {
  if (unit.kind === 'planned') return <span className="badge planned">Запланирована</span>;
  if (!unit.progress) return <span className="badge">Нет Progress</span>;
  return <span className={`badge ${unit.progress.status}`}>{statuses[unit.progress.status]}</span>;
}

const impactOrder = { blocking: 0, important: 1, minor: 2 };
const statusOrder = { confirmed: 0, detected: 1 };
const dimensionOrder = Object.keys(dimensions);

function Gaps({ gaps, titles }) {
  if (!gaps.length) return <p className="muted">Активных Gaps нет.</p>;
  const sorted = [...gaps].sort((a, b) => impactOrder[a.routing_impact] - impactOrder[b.routing_impact]
    || statusOrder[a.status] - statusOrder[b.status]
    || dimensionOrder.indexOf(a.dimension) - dimensionOrder.indexOf(b.dimension));
  return <div className="gap-list">{sorted.map((gap) => <div className={`gap-card ${gap.routing_impact}`} key={gap.id}>
    <div><strong>{dimensions[gap.dimension]}</strong><span className="badge gap">{gapStatuses[gap.status]}</span></div>
    <Link to={`/nodes/${gap.node}`}>{titles.get(gap.node) || gap.node}</Link>
    <small><span className={`impact ${gap.routing_impact}`}>{impacts[gap.routing_impact] || gap.routing_impact}</span> · {scopes[gap.scope] || gap.scope}</small>
  </div>)}</div>;
}

function NodeLinks({ nodes, empty = 'Нет связей.' }) {
  return nodes.length ? <div className="node-links">{nodes.map((node) =>
    <Link key={node.id} to={`/nodes/${node.id}`}><span className={`dot ${node.type}`} />{node.title}<span aria-hidden="true">›</span></Link>)}</div>
    : <p className="muted">{empty}</p>;
}

function UnitList({ units }) {
  if (!units.length) return <p className="muted">Нет связанных Units.</p>;
  return <div className="unit-list">{units.map((unit) => <Link className="unit-card" key={unit.id} to={`/units/${unit.id}`}>
    <div><ProgressBadge unit={unit} /><span aria-hidden="true">›</span></div>
    <strong>{unit.title}</strong>
    {unit.kind === 'initialized' && unit.in_frontier && <small>Также во Frontier</small>}
  </Link>)}</div>;
}

function PanelHeading() {
  return <div className="panel-heading"><span className="eyebrow">ДЕТАЛИ УЗЛА</span><Link to="/" className="close" aria-label="Закрыть панель">×</Link></div>;
}

function NodePanel({ id, hierarchy, occurrence }) {
  const { data, error, loading } = useResource(`/api/nodes/${encodeURIComponent(id)}`);
  if (error) return <aside className="inspector"><PanelHeading /><Message error title="Не удалось открыть узел">{error}</Message></aside>;
  if (!data) return <aside className="inspector"><PanelHeading /><Message title="Загрузка узла…" /></aside>;
  const { node, parents, children, edges, related_nodes, units, gaps } = data;
  const path = (node.id === id && occurrence?.split('/')) || hierarchy.paths.get(node.id) || [node.id];
  const initialized = units.filter((unit) => unit.kind === 'initialized');
  const planned = units.filter((unit) => unit.kind === 'planned');
  const relations = edges.map((edge) => {
    const outgoing = edge.source === node.id;
    const otherId = outgoing ? edge.target : edge.source;
    return { edge, otherId, label: relationLabels[edge.type][outgoing ? 'out' : 'in'], other: related_nodes.find((item) => item.id === otherId) };
  }).sort((a, b) => a.label.localeCompare(b.label, 'ru'));
  return <aside className={`inspector ${loading ? 'stale' : ''}`} aria-label="Выбранный узел" aria-busy={loading}>
    <PanelHeading />
    <span className={`badge type-${node.type}`}>{typeLabels[node.type]}</span>
    <h2>{node.title}</h2><code className="record-id">{node.id}</code>
    {node.status === 'deprecated' && <span className="badge">Устаревший узел</span>}
    <p className="description">{node.summary || 'Описание пока не добавлено.'}</p>
    <section><h3>Место на карте</h3><div className="breadcrumbs">{path.map((key, index) => <React.Fragment key={key}>
      {index > 0 && <span> / </span>}<Link to={`/nodes/${key}`}>{hierarchy.byId.get(key)?.title || key}</Link>
    </React.Fragment>)}</div>
      <h4>Родители{parents.length > 1 ? ' · несколько представлений на карте' : ''}</h4>
      <NodeLinks nodes={parents} empty="Нет родителей. Узел находится в корне или в циклической компоненте без корня." />
      <h4>Дочерние узлы</h4><NodeLinks nodes={children} empty="Нет дочерних узлов." />
    </section>
    <section><h3>Учебные Units <span>{initialized.length}</span></h3>
      <UnitList units={initialized} />
      <h3>Запланированные Units <span>{planned.length}</span></h3>
      <UnitList units={planned} />
    </section>
    <section><h3>Активные Gaps <span>{gaps.length}</span></h3><Gaps gaps={gaps} titles={new Map([[node.id, node.title]])} /></section>
    <section><h3>Все прямые связи</h3>{relations.length ? <ul className="relation-list">{relations.map(({ edge, otherId, label, other }) =>
      <li key={`${edge.type}:${edge.source}:${edge.target}`}><small>{label}</small><Link to={`/nodes/${otherId}`}>{other?.title || otherId}</Link></li>)}</ul>
      : <p className="muted">Нет связей.</p>}</section>
    <p className="footnote">Units и Gaps относятся только к этому узлу.</p>
    <Warnings warnings={data.warnings} />
  </aside>;
}

function ProgressDetails({ progress }) {
  const { review } = progress;
  const facts = [];
  if (progress.attempts != null) facts.push(['Попыток', progress.attempts]);
  if (progress.last_attempt) facts.push(['Последняя попытка', formatDate(progress.last_attempt)]);
  // Review scheduling applies to verified Units only; the overdue value comes from the engine.
  if (progress.status === 'verified' && review?.due) {
    facts.push(['Следующий Review', <>{formatDate(review.due)}{progress.review_overdue_days != null
      && <span className="badge overdue">{progress.review_overdue_days ? `просрочен на ${progress.review_overdue_days} ${plural(progress.review_overdue_days, ['день', 'дня', 'дней'])}` : 'сегодня'}</span>}</>]);
  }
  if (!facts.length) return null;
  return <dl className="progress-facts">{facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function UnitPage({ id }) {
  const { data, error, loading } = useResource(`/api/units/${encodeURIComponent(id)}`);
  useEffect(() => {
    if (data?.unit) document.title = `${data.unit.title} · Learning`;
    return () => { document.title = 'Карта знаний · Learning'; };
  }, [data]);
  if (error) return <div className="unit-page"><Link to="/" className="back-link">← К карте знаний</Link><Message error title="Не удалось открыть Unit">{error}</Message></div>;
  if (!data) return <Message title="Загрузка Unit…" />;
  const { unit, nodes, gaps } = data;
  return <article className={`unit-page ${loading ? 'stale' : ''}`} aria-busy={loading}>
    <div className="unit-heading"><span className="eyebrow">{unit.kind === 'planned' ? 'ЗАПЛАНИРОВАННАЯ UNIT' : 'УЧЕБНАЯ UNIT'}</span><ProgressBadge unit={unit} /></div>
    <h1>{unit.title}</h1><code className="record-id">{unit.id}</code>
    <p className="unit-goal">{unit.goal || 'Описание пока не добавлено.'}</p>
    {unit.kind === 'initialized' && unit.in_frontier && <p className="muted">Эта Unit также присутствует во Frontier.</p>}
    <section><h2>Текущий Progress</h2>
      {unit.progress ? <><p className="muted">Последние сохранённые результаты Unit</p><div className="grade-grid">{Object.entries(dimensions).map(([key, label]) =>
        <div className="grade-card" key={key}><span>{label}</span><strong className={`grade ${unit.progress.mastery[key] || 'none'}`}>{grades[unit.progress.mastery[key]] || 'Нет данных'}</strong></div>)}</div>
        <ProgressDetails progress={unit.progress} /></>
        : <p className="muted">{unit.kind === 'planned' ? 'Unit пока только запланирована. Progress отсутствует.' : 'Для этой Unit ещё нет сохранённого Progress.'}</p>}
    </section>
    <div className="unit-columns"><section><h2>Связанные узлы</h2><NodeLinks nodes={nodes} /></section>
      <section><h2>Активные Gaps <span className="count">{gaps.length}</span></h2><Gaps gaps={gaps} titles={new Map(nodes.map((node) => [node.id, node.title]))} /></section></div>
    <Warnings warnings={data.warnings} />
  </article>;
}

function KnowledgeNode({ data, selected }) {
  const children = `${data.childCount} ${plural(data.childCount, ['дочерний узел', 'дочерних узла', 'дочерних узлов'])}`;
  return <div className={`knowledge-node ${data.type} ${selected ? 'chosen' : ''} ${data.cycle ? 'cyclic' : ''}`}>
    <Handle type="source" position={Position.Left} />
    <button className="node-body nodrag" onClick={data.onSelect} aria-label={`Открыть ${data.title}`} aria-current={selected ? 'true' : undefined}>
      <span className="node-type">{typeLabels[data.type]}
        {data.parentCount > 1 && ` · ${data.parentCount} ${plural(data.parentCount, ['родитель', 'родителя', 'родителей'])}`}
        {data.rootless && ' · без корня'}</span>
      <strong>{data.title}</strong>
      {data.cycle && <small>↩ Циклическая связь · перейти к узлу</small>}
    </button>
    {!data.cycle && data.childCount > 0 && <button className="expand-node nodrag" onClick={data.onToggle}
      aria-label={`${data.open ? 'Свернуть' : 'Раскрыть'} ${data.title}: ${children}`} title={`${data.open ? 'Свернуть' : 'Раскрыть'} · ${children}`} aria-expanded={data.open}>
      <span aria-hidden="true">{data.open ? '−' : '+'}</span><small aria-hidden="true">{data.childCount}</small>
    </button>}
    <Handle type="target" position={Position.Right} />
  </div>;
}

const nodeTypes = { knowledge: KnowledgeNode };
const fitViewOptions = { padding: 0.15, minZoom: 0.5, maxZoom: 1 };

function MapCanvas({ hierarchy, map, selectedId, onSelect, expanded, setExpanded, focus }) {
  const [links, setLinks] = useState({ prerequisite: false, related: false });
  const { setCenter, getZoom, fitView } = useReactFlow();
  // Layout positions are computed here, so only the pan/zoom instance must exist.
  const [flowReady, setFlowReady] = useState(false);
  const viewportReady = useRef(false);
  const centered = useRef(null);
  const onToggle = useCallback((id) => setExpanded((previous) => {
    const next = new Set(previous);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  }), [setExpanded]);
  const projection = useMemo(() => projectHierarchy(hierarchy, expanded, selectedId,
    { onSelect, onToggle }, map.edges.filter((edge) => links[edge.type])),
  [hierarchy, expanded, selectedId, onSelect, onToggle, map.edges, links]);
  // The initial viewport either fits the map or, for a direct link, centers the
  // selected Node; ReactFlow's own fitView would run later and override it.
  // Each focus request centers once, so expanding other branches later does
  // not pull the viewport back.
  useEffect(() => {
    if (!flowReady) return;
    const pending = focus?.id && centered.current !== focus.nonce;
    const target = pending && projection.nodes.find((node) => node.id === focus.id);
    const first = !viewportReady.current;
    viewportReady.current = true;
    if (!target) {
      if (first) fitView(fitViewOptions);
      return;
    }
    centered.current = focus.nonce;
    setCenter(target.position.x + 130, target.position.y + 45,
      { zoom: first ? 0.85 : focus.keepZoom ? getZoom() : Math.max(getZoom(), 0.8), duration: first ? 0 : 350 });
  }, [focus, projection.nodes, setCenter, getZoom, fitView, flowReady]);
  return <div className="map-canvas">
    <div className="map-toolbar">
      <span className="eyebrow">СВЯЗИ</span>
      <span className="link-key part-of"><i aria-hidden="true" />Иерархия</span>
      {Object.entries(linkLabels).map(([type, label]) => <label key={type} className={`link-key ${type}`}>
        <input type="checkbox" checked={links[type]} onChange={(event) => setLinks({ ...links, [type]: event.target.checked })} />
        <i aria-hidden="true" />{label}</label>)}
      <div className="map-legend" aria-label="Типы узлов"><span><i className="dot area" />Область</span><span><i className="dot topic" />Тема</span><span><i className="dot concept" />Понятие</span></div>
    </div>
    <div className="flow-area">
      <ReactFlow nodes={projection.nodes} edges={projection.edges} nodeTypes={nodeTypes}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}
        onInit={() => setFlowReady(true)} minZoom={0.15} maxZoom={1.7}
        ariaLabelConfig={{ 'controls.zoomIn.ariaLabel': 'Приблизить', 'controls.zoomOut.ariaLabel': 'Отдалить', 'controls.fitView.ariaLabel': 'Показать всю карту' }}>
        <Background color="#d4d9d1" gap={22} size={1} /><Controls showInteractive={false} />
      </ReactFlow>
    </div>
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
  // A few roots open at once keep the first view readable; larger maps start collapsed.
  useEffect(() => { setExpanded(new Set(hierarchy.roots.length <= 3 ? hierarchy.roots.map(({ id }) => id) : [])); }, [hierarchy]);

  const reveal = useCallback((id, preferredOccurrence = null, keepZoom = false) => {
    const path = preferredOccurrence?.split('/') || hierarchy.paths.get(id);
    if (!path) return;
    setExpanded((previous) => {
      const next = new Set(previous);
      for (let index = 1; index < path.length; index += 1) next.add(occurrenceId(path.slice(0, index)));
      return next;
    });
    setFocus({ id: occurrenceId(path), nonce: Date.now(), keepZoom });
  }, [hierarchy]);

  // Search, browser navigation, direct URLs, and links from Unit pages all open
  // ancestor occurrences. Clicking a visible duplicate preserves its branch.
  useEffect(() => {
    if (selectedId) reveal(selectedId, location.state?.occurrence, location.state?.fromMap);
  }, [selectedId, hierarchy, reveal, location.key, location.state]);
  const selectNode = useCallback((id, occurrence = null) => {
    navigate(`/nodes/${id}`, { state: { occurrence, fromMap: occurrence !== null } });
  }, [navigate]);
  const openSearchResult = (id) => {
    if (window.matchMedia(MOBILE).matches) setQuery('');
    navigate(`/nodes/${id}`);
  };

  const needle = query.trim().toLocaleLowerCase();
  const searchResults = needle ? [...hierarchy.byId.values()].filter((node) =>
    [node.title, node.id, node.summary || ''].some((text) => text.toLocaleLowerCase().includes(needle)))
    .sort((a, b) => Number(!a.title.toLocaleLowerCase().includes(needle)) - Number(!b.title.toLocaleLowerCase().includes(needle))
      || a.title.localeCompare(b.title)) : [];

  const currentTitle = unitId ? 'Unit'
    : selectedId ? hierarchy.byId.get(selectedId)?.title || (map ? 'Узел не найден' : '…')
    : unknownRoute ? 'Страница не найдена' : null;

  const content = unitId ? <UnitPage id={unitId} />
    : loading && !map ? <Message title="Загрузка карты…" />
    : error ? <Message error title="Карта недоступна">{error}</Message>
    : unknownRoute ? <Message error title="Страница не найдена"><Link to="/">Открыть карту знаний</Link></Message>
    : map.repository_state === 'uninitialized' ? <Message title="Тема ещё не инициализирована">В этом репозитории пока нет карты знаний. Начните обучение через агента или запустите интерфейс с флагом --demo для знакомства.</Message>
    : !map.nodes.length ? <Message title="Карта пока пуста">В репозитории нет доступных Graph Nodes.</Message>
    : <div className="map-workspace"><h1 className="sr-only">Карта знаний</h1>
      <ReactFlowProvider><MapCanvas hierarchy={hierarchy} map={map} selectedId={selectedId} expanded={expanded} setExpanded={setExpanded} focus={focus} onSelect={selectNode} /></ReactFlowProvider>
      {selectedId && <NodePanel id={selectedId} hierarchy={hierarchy} occurrence={location.state?.occurrence} />}
    </div>;

  return <div className="app-shell">
    <aside className="sidebar">
      <Link className="brand" to="/"><span className="brand-mark">⌘</span><span>Learning<small>ЛИЧНАЯ БАЗА ЗНАНИЙ</small></span></Link>
      <div className="sidebar-section"><span className="eyebrow">ПРОСТРАНСТВО ОБУЧЕНИЯ</span>
        <Link className="nav-current" to="/" aria-current={!unitId ? 'page' : undefined}><span>⌘</span>Карта знаний</Link>
      </div>
      <div className="sidebar-section search-section"><label className="eyebrow" htmlFor="node-search">НАЙТИ НА КАРТЕ</label>
        <div className="search-box"><span aria-hidden="true">⌕</span>
          <input id="node-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Escape') setQuery(''); }} placeholder="Название или ID узла…" autoComplete="off" />
          {query && <button className="search-clear" onClick={() => setQuery('')} aria-label="Очистить поиск">×</button>}
        </div>
        {needle && <div className="search-results" aria-live="polite"><small>Найдено: {searchResults.length}</small>
          {searchResults.map((node) => <button key={node.id} onClick={() => openSearchResult(node.id)} aria-current={node.id === selectedId ? 'true' : undefined}>
            <span className={`dot ${node.type}`} /><span>{node.title}<small>{typeLabels[node.type]} · {node.id}</small></span><span aria-hidden="true">›</span></button>)}
          {!searchResults.length && <p className="muted">Совпадений нет.</p>}
        </div>}
      </div>
      <div className="sidebar-section roots-nav"><span className="eyebrow">НАЧАЛО КАРТЫ</span>
        {hierarchy.roots.map((root) => <button key={root.id} onClick={() => selectNode(root.id)} aria-current={root.id === selectedId ? 'true' : undefined}>
          <span className={`dot ${hierarchy.byId.get(root.id).type}`} />{hierarchy.byId.get(root.id).title}{root.cyclic && <small title="Циклическая компонента без корня">↩</small>}</button>)}
      </div>
      <div className="sidebar-footer"><span className={`mode-dot ${map?.mode === 'demo' ? 'demo' : ''}`} /><div>{map?.mode === 'demo' ? 'Демонстрационный режим' : 'Локальный репозиторий'}<small>Только чтение · без синхронизации</small></div></div>
    </aside>
    <div className="workspace">
      <header className="workspace-header">
        <nav className="crumbs" aria-label="Расположение">
          {currentTitle ? <Link to="/">Карта знаний</Link> : <strong>Карта знаний</strong>}
          {currentTitle && <><span className="slash" aria-hidden="true">/</span><strong>{currentTitle}</strong></>}
        </nav>
        <div className="header-meta">
          {map?.nodes.length > 0 && <span className="map-counts">{map.nodes.length} {plural(map.nodes.length, ['узел', 'узла', 'узлов'])} · {map.edges.length} {plural(map.edges.length, ['связь', 'связи', 'связей'])}</span>}
          {map?.mode === 'demo' && <span className="badge demo-badge">DEMO</span>}
          <span className="readonly">Только чтение</span>
        </div>
      </header>
      {map && <Warnings warnings={map.warnings} />}
      {content}
    </div>
  </div>;
}

createRoot(document.getElementById('root')).render(<BrowserRouter><App /></BrowserRouter>);
