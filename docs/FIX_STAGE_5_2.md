Нужно исправить Stage 5 graph expansion так, чтобы новые learning interests **интегрировались в существующий graph**, а не создавали параллельные или дублирующие ветки.

Не переделывай Stage 5 целиком. Это hardening существующей логики `Interest → graph expansion`.

## Проблема

В acceptance-test пользователь добавил interest:

```text
Хочу лучше разобраться в:
- document databases
- wide-column databases
- graph databases
```

Codex корректно создал новые concept nodes, но также создал новый top-level parent:

```text
data-models
├── document-databases
├── wide-column-databases
└── graph-databases
```

При этом в существующем graph уже была близкая ветка:

```text
data-systems
└── storage-selection
```

В результате возникла параллельная taxonomy вместо расширения существующей.

Для небольшого automatic graph expansion это нежелательно.

Главный новый принцип:

> Graph expansion is integration-first.

То есть сначала нужно попытаться встроить новые знания в существующую структуру, и только если это невозможно — создавать новый grouping node или новую top-level branch.

---

# 1. Усилить `capture-interest` skill

Проверь:

```text
.agents/skills/capture-interest/SKILL.md
```

и связанные graph-expansion instructions.

Добавь явные правила.

Перед созданием любого нового parent/topic/area node Codex должен:

```text
1. Search the existing graph for semantic attachment candidates.
2. Prefer attaching new leaf/concept nodes to an existing suitable parent.
3. Do not create a new grouping node if an existing node already represents
   the same or sufficiently close learning dimension.
4. A new intermediate parent is allowed only when:
   - no existing node is a reasonable semantic parent;
   - the new parent represents a genuinely distinct concept,
     not a synonym/rephrasing;
   - adding it improves the current hierarchy rather than starting a
     parallel taxonomy.
5. Small automatic graph expansion must remain anchored to the
   pre-existing graph.
```

Зафиксируй приоритет:

```text
reuse existing node
→ attach new child to existing branch
→ add new intermediate node
→ add new top-level area
```

Новый top-level `area` должен быть самым дорогим вариантом.

---

# 2. Добавить общий graph invariant в SPEC

Проверь:

```text
docs/SPEC.md
```

Добавь общий принцип graph evolution:

```text
Graph expansion is integration-first.

When adding knowledge:
- reuse semantically suitable existing nodes and branches;
- prefer extending an existing branch over creating a parallel hierarchy;
- new grouping nodes must add real semantic structure,
  not merely group newly requested concepts;
- automatically applied graph deltas must remain anchored
  to the pre-existing graph;
- a new disconnected/top-level branch is a structural change
  and requires explicit semantic justification or user confirmation.
```

Это должно быть общим правилом graph evolution, не только для interests.

---

# 3. Исправить misleading example в Stage 5 plan/docs

Проверь:

```text
docs/PLAN_STAGE_5.md
```

Если там есть пример вроде:

```text
data-models
├── document-databases
├── wide-column-databases
└── graph-databases
```

замени его на пример, который сначала использует существующую ветку.

Например:

```text
existing storage-selection
├── document-databases
├── wide-column-databases
└── graph-databases
```

и добавь пояснение:

```text
Create a new parent only when no suitable existing parent exists.
```

Важно: docs не должны подталкивать Codex к созданию нового `data-models` просто ради группировки новых nodes.

---

# 4. Добавить deterministic guardrail для graph delta

Нужно защитить automatic small graph expansion от создания нового изолированного subgraph.

Проверь текущую реализацию graph expansion / apply delta / validator.

Добавь проверку примерно такого смысла:

```text
old graph = G
new nodes introduced by delta = N

For every connected component containing nodes from N,
there must be a path to at least one node that existed in G.
```

То есть такой automatic delta должен быть отклонён:

```text
OLD GRAPH

data-systems
└── storage-selection


NEW DISCONNECTED COMPONENT

data-models
├── document-databases
├── wide-column-databases
└── graph-databases
```

Желательная ошибка:

```text
Graph delta introduces a new component not anchored to the existing graph.
Attach it to an existing node or explicitly approve a new root branch.
```

Это guardrail только против structural isolation.

Он НЕ должен пытаться детерминированно решать semantic duplication вроде:

```text
data-models vs storage-selection
```

Семантический выбор остаётся задачей Codex.

---

# 5. Не запрещать несколько top-level areas вообще

Важно:

не вводи глобальное правило:

```text
graph may only have one root
```

или:

```text
new top-level areas are forbidden
```

В большой learning topic несколько top-level areas нормальны.

Ограничение относится только к:

```text
small automatic graph expansion
```

из interest/gap-driven evolution.

Если действительно обнаружена новая самостоятельная область, Codex может:

```text
propose structural graph delta
→ explain why it is separate
→ request user confirmation
```

---

# 6. Acceptance behavior for the current example

Для текущего System Design graph:

```text
data-systems
└── storage-selection
```

и interest:

```text
document databases
wide-column databases
graph databases
```

предпочтительный результат:

```text
data-systems
└── storage-selection
    ├── document-databases
    ├── wide-column-databases
    └── graph-databases
```

Не создавать новый:

```text
data-models
```

если `storage-selection` является разумным semantic parent.

Важно: это пример поведения, а не hardcoded special case для этих ID.

---

# 7. Tests

Добавь tests минимум для следующих сценариев.

## Existing suitable parent

Исходный graph содержит:

```text
storage-selection
```

Interest требует:

```text
document-databases
graph-databases
```

Ожидаемо:

```text
new concepts attach to existing branch
no unnecessary grouping node
```

Если semantic attachment относится к skill-level logic и неудобен для unit test, хотя бы зафиксируй соответствующее skill behavior через fixture/integration test.

---

## Automatic disconnected subtree rejected

Old graph:

```text
root-a
└── existing-topic
```

Delta создаёт:

```text
new-area
└── new-concept
```

и не соединяет его с old graph.

Ожидаемо:

```text
automatic expansion rejected
```

---

## Anchored subtree accepted

Delta:

```text
existing-topic
└── new-concept
```

Ожидаемо:

```text
accepted
```

---

## Multiple roots remain valid

Исходный graph уже имеет несколько legitimate top-level areas.

Validation должна продолжать проходить.

---

# 8. Preserve existing architecture

Не ломать:

```text
durable graph IDs
Interest lifecycle
Gap lifecycle
adaptive frontier
routing reasons
Stage 1–4 behavior
```

Не добавлять:

```text
global ontology engine
automatic semantic deduplication system
graph migration framework
large-scale graph normalization
```

Это небольшой hardening fix.

---

# 9. Current test branch cleanup

Не обязательно автоматически менять пользовательскую test branch, если implementation работает только с template/main.

Но в summary укажи, как вручную исправить уже созданный test graph:

```text
remove unnecessary data-models node
remove its part-of edges
attach document-databases / wide-column-databases / graph-databases
to the existing suitable parent
```

---

# 10. Verification

После изменений запусти:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/learning.py validate
```

Если команды отличаются — используй актуальные.

В финальном summary укажи:

1. какие skills/docs изменены;
2. какое integration-first правило добавлено;
3. какой deterministic guardrail добавлен;
4. как automatic delta отличается от structural delta;
5. какие tests добавлены;
6. проходят ли regression tests Stage 1–5;
7. как вручную поправить текущий `test_stage_5` graph.
