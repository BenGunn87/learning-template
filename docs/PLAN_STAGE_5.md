Нужно реализовать **Stage 5 — Adaptive Routing & Gap Detection** в текущем `learning-template`.

Не переделывай архитектуру предыдущих Stage. Stage 5 должен расширить существующую модель, сохранив все принципы Stage 1–4.

## Цель Stage 5

Маршрут обучения должен учитывать не только graph/progress, но и два новых вида сигналов:

```text
detected gaps
+
user-declared interests
+
current context/goal
+
graph prerequisites
→ adaptive frontier
```

Нужно добавить две новые Primary Data сущности:

```text
Gap
Interest
```

и научить frontier учитывать их.

---

# 1. Gap

Gap — отдельная Primary Data сущность, а не вычисляемый флаг Progress.

Предлагаемая директория:

```text
gaps/
```

Можно использовать один YAML на gap:

```text
gaps/<gap-id>.yaml
```

## Lifecycle

```text
detected → confirmed → resolved
                      ↓
                reopened/confirmed
```

Не обязательно вводить отдельный status `reopened`.

Можно при новом weak signal переводить:

```text
resolved → confirmed
```

с записью события в history.

## Базовая структура

Пример:

```yaml
format_version: 1
id: gap-data-model-selection-001

created_at: ...

node: data-model-selection
dimension: application

status: confirmed

scope: local
routing_impact: important

signals:
  - evidence: 2026-09-16-003-initial-001
    assessment: ...
    result: hard
    observed_nodes:
      - data-model-selection

history:
  - status: detected
    at: ...
    evidence: ...

  - status: confirmed
    at: ...
    evidence: ...

resolved_at: null
```

Точную schema адаптируй к стилю проекта.

---

# 2. Gap detection

Assessment остаётся источником weak signals.

Weak signal:

```text
hard
failed
```

по одной из dimensions:

```text
recall
understanding
application
```

Первый weak signal:

```text
no gap
→ create detected gap
```

Второй независимый weak signal:

```text
detected
→ confirmed
```

Независимый означает новую Evidence, а не два наблюдения внутри одной Evidence.

Особенно сильное подтверждение — если проблема проявилась в другой Unit, связанной с тем же graph node.

Не подтверждай gap только потому, что одна Assessment содержит несколько `hard/failed`.

---

# 3. Resolving gaps

Confirmed gap может стать `resolved`, если последующая Evidence специально проверяет слабое место и соответствующая dimension становится:

```text
good
easy
```

Не требуй двух успешных Evidence для MVP.

Если после `resolved` появляется новый weak signal по тому же node + dimension:

```text
resolved → confirmed
```

Не создавай новый gap.

History должна сохранять все переходы.

---

# 4. Gap granularity

Gap должен начинаться максимально узко.

Правило:

```text
Create gap on the lowest meaningful graph node
that was actually tested by the Evidence.
```

Не поднимай автоматически:

```text
quorum gap
→ replication gap
```

только потому, что `replication` — parent.

## Scope

Добавь:

```text
scope:
  local
  cross-concept
```

`local` — gap относится к конкретному concept.

`cross-concept` — несколько независимых weak signals из связанных child concepts указывают на общую проблему более высокого уровня.

Расширение gap вверх должно происходить только при:

1. нескольких независимых signals;
2. signals из нескольких связанных graph nodes;
3. semantic judgment Codex, что это одна общая проблема.

Deterministic core может находить кандидатов, но не должен сам делать semantic inference вида:

```text
2 weak children → parent gap
```

---

# 5. Routing impact

Gap должен иметь:

```text
routing_impact:
  blocking
  important
  minor
```

## blocking

Только confirmed gap.

Gap blocking, если его node является prerequisite для:

* текущей Unit;
* ближайшей Unit primary route;
* или ближайшей technically-available ветки primary focus.

Проверку prerequisite relationships должен делать deterministic core.

`blocking` действительно может ограничивать продвижение дальше по зависимой ветке.

## important

Gap не блокирует graph prerequisite напрямую, но:

* node является `core`;
* относится к primary focus;
* явно связан с текущей goal/context;
* либо существенно влияет на ближайший маршрут.

Он повышает priority frontier, но не блокирует остальные Units.

## minor

Локальная слабость, не мешающая ближайшему маршруту.

Остаётся в backlog и может закрываться позже.

---

# 6. Remediation

Не делай:

```text
confirmed gap → always create new Unit
```

Gap описывает проблему.

Remediation — решение routing.

Примерная логика:

```text
forgetting previously verified material
→ review

weak application
→ targeted practice

weak understanding
→ existing or new study Unit

missing prerequisite
→ prerequisite Unit
```

По возможности используй существующую Unit.

Создавай новую remedial Unit только если существующая Unit слишком широкая или не подходит.

Gap и remediation не должны быть одной сущностью.

---

# 7. Interest

Добавь новую Primary Data сущность:

```text
interests/
```

Например:

```text
interests/<interest-id>.yaml
```

## Lifecycle

```text
pending → active → satisfied
                 ↓
              dismissed
```

### pending

Пользователь явно добавил тему, но frontier её ещё не обслуживает.

### active

Во frontier появилась хотя бы одна Unit, выбранная для обслуживания этого interest.

### satisfied

Для текущей цели interest получил достаточное покрытие.

Не определяй `satisfied` просто по количеству Units.

Codex должен учитывать:

* original request;
* related graph nodes;
* progress/evidence по ним;
* текущую learning goal.

### dismissed

Пользователь явно больше не хочет развивать эту тему.

---

# 8. Interest structure

Пример:

```yaml
format_version: 1
id: interest-non-relational-databases

created_at: ...
source: user

request: >
  Хочу лучше разобраться в document databases,
  wide-column databases и graph databases.

related_nodes:
  - document-databases
  - wide-column-databases
  - graph-databases

status: pending

history:
  - status: pending
    at: ...
```

---

# 9. Adding interests

Нужен естественный UX.

Пользователь может сказать, например:

```text
Хочу позже глубже изучить graph databases.
```

или:

```text
Добавь в темы для изучения document и wide-column databases.
```

Codex должен:

1. распознать explicit learning interest;
2. найти соответствующие graph nodes;
3. создать Interest;
4. при необходимости минимально расширить graph;
5. не делать эту тему автоматически следующей Unit.

Interest влияет на priority frontier, но не является hard override.

Если пользователь явно говорит:

```text
давай это следующим
```

это уже user override, а не обычный interest.

---

# 10. Interest-driven graph expansion

Если нужные nodes уже есть:

```text
link interest → existing nodes
```

Если graph слишком грубый:

```text
add minimal meaningful graph layer
```

Например:

```text
data-models
├── document-databases
├── wide-column-databases
└── graph-databases
```

Не создавай сразу большую детальную ветку про MongoDB/Cassandra/Neo4j.

Принцип:

```text
Add the nearest meaningful layer only.
Expand further as learning progresses.
```

Небольшое однозначное расширение graph можно применять автоматически.

Крупное или неоднозначное изменение должно быть сначала предложено пользователю как graph delta.

---

# 11. Adaptive frontier

Stage 5 frontier должен учитывать:

```text
graph
progress
confirmed gaps
pending/active interests
context
diagnostic
prerequisites
```

Высокоуровневая схема:

```text
graph + progress
        ↓
technical availability
        ↓
gaps + interests + context
        ↓
Codex prioritization
        ↓
frontier skeleton Units
```

Deterministic core отвечает:

```text
Can this Unit/node be studied?
Is a prerequisite blocked?
Which gaps/interests relate to this node?
```

Codex отвечает:

```text
What is worth studying next?
Which remediation is appropriate?
How should interests compete with the primary route?
```

---

# 12. Frontier priority behavior

Не превращай frontier в строгую очередь.

Примерный порядок влияния:

```text
blocking gap
→ remediation before dependent branch

important gap
→ high priority

primary route
→ continues normally

active/pending interest
→ raises priority of related branch

minor gap
→ opportunistic/backlog
```

Не делай правило:

```text
every confirmed gap must be the next Unit
```

Система не должна зацикливаться только на исправлении слабостей.

---

# 13. Routing reason

Каждая skeleton Unit во frontier должна уметь объяснить, почему она там появилась.

Добавь routing reason.

Например:

```yaml
routing_reason:
  type: gap
  gap: gap-data-model-selection-001
```

или:

```yaml
routing_reason:
  type: interest
  interest: interest-non-relational-databases
```

или:

```yaml
routing_reason:
  type: primary-route
```

Допускается несколько причин, если текущая schema лучше поддерживает список:

```yaml
routing_reasons:
  - type: primary-route
  - type: interest
    interest: ...
```

Выбери вариант, который лучше соответствует текущей архитектуре.

Главный инвариант:

> Система должна уметь объяснить, почему конкретная Unit появилась во frontier.

---

# 14. Existing architecture constraints

Не ломай следующие принципы.

```text
Graph Node = what needs to be known
Unit = concrete learning action
Evidence = immutable fact
Assessment = append-only interpretation
Progress = Derived
Frontier = Derived
Gap = Primary
Interest = Primary
```

Также сохранить:

* one unfinished Session invariant;
* Stage 4 pause/resume/recovery;
* review logic Stage 3;
* targeted practice;
* user override;
* prerequisite warning rather than unnecessary hard blocking;
* durable graph IDs;
* PRIMARY > DERIVED.

Не добавляй database.

Repository остаётся source of truth.

---

# 15. CLI / deterministic core

Добавь минимальные deterministic operations, необходимые для:

* list gaps;
* list interests;
* create/update interest;
* inspect related graph nodes;
* detect candidate weak signals;
* rebuild/update routing metadata;
* validate gaps/interests;
* compute prerequisite impact.

Не обязательно делать сложный CLI UX, если skills используют internal scripts.

Следуй текущему стилю проекта.

---

# 16. Skills

Добавь или обнови skills для:

### Interest capture

Codex должен уметь распознать фразы вроде:

```text
Хочу лучше разобраться в graph databases.
Добавь Kafka в темы для изучения.
Позже хочу подробнее пройти observability.
```

И сохранить Interest.

### Gap handling

После Assessment:

```text
weak signal
→ update/create gap
→ possibly update routing impact
→ update/rebuild frontier
```

### Frontier generation

Frontier skill должен читать:

```text
gaps/
interests/
```

и учитывать их при prioritization.

---

# 17. Acceptance tests

Добавь unit/integration tests минимум для следующих сценариев.

## Gap detected

Первая Evidence:

```text
application: hard
```

создаёт:

```text
status: detected
```

но ещё не confirmed.

## Gap confirmed

Вторая независимая Evidence по тому же node + dimension:

```text
application: hard
```

переводит:

```text
detected → confirmed
```

## Gap resolved

Targeted practice:

```text
application: good
```

переводит:

```text
confirmed → resolved
```

## Gap reopened

Новая Evidence:

```text
application: hard
```

после resolved:

```text
resolved → confirmed
```

без создания нового gap ID.

## No false parent promotion

Weak signal по:

```text
quorum
```

не должен автоматически создавать gap по:

```text
replication
```

## Blocking gap

Confirmed gap по prerequisite node должен корректно влиять на availability/routing dependent branch.

## Interest creation

Explicit user interest должен создавать persistent Interest со status:

```text
pending
```

## Interest activates

Когда frontier начинает обслуживать Interest:

```text
pending → active
```

## Graph expansion

Interest по теме, которой нет в graph, должен позволить добавить минимальный meaningful node layer.

## Frontier routing reasons

Frontier Unit должна иметь explainable routing reason.

## Regression

Все Stage 1–4 tests должны продолжать проходить.

---

# 18. Realistic System Design example

Используй текущий System Design test repo как мысленную acceptance model.

Пользователь после Unit про data models говорит:

```text
Хочу глубже изучить:
- document databases
- wide-column databases
- graph databases
```

Ожидаемо:

1. создаётся Interest;
2. graph проверяется;
3. если этих nodes нет — добавляется минимальный слой;
4. Interest остаётся `pending`;
5. при следующем frontier rebuild связанные Units получают повышенный priority;
6. primary route не обязан немедленно переключаться на них;
7. когда хотя бы одна такая Unit реально попадает в обслуживаемый frontier/маршрут — Interest становится `active`.

---

# 19. Scope exclusions

Не включать в Stage 5:

* Web UI;
* multi-agent;
* automatic large-scale graph restructuring;
* long-inactivity recalibration;
* advanced analytics;
* assessment re-evaluation framework;
* migration framework;
* sophisticated probabilistic mastery model;
* automatic merging of gaps with no semantic review.

Keep Stage 5 focused on:

```text
gaps
interests
adaptive frontier
explainable routing
```

---

# 20. Verification

После реализации запусти:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/learning.py validate
```

Если реальные команды отличаются — используй актуальные команды проекта.

В конце дай summary:

1. новые файлы/directories;
2. schema Gap;
3. schema Interest;
4. lifecycle обоих;
5. как работает gap detection;
6. как определяется routing impact;
7. как Interest влияет на graph/frontier;
8. как теперь формируются routing reasons;
9. какие tests добавлены;
10. подтверждение, что Stage 1–4 regression tests проходят.
