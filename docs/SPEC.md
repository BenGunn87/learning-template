# Learning System — MVP Specification v0.5

## 1. Цель

Система предназначена для систематического изучения произвольной большой темы короткими учебными сессиями.

Она должна помогать:

* декомпозировать тему в карту знаний;
* адаптировать маршрут под цель и текущий уровень;
* учиться короткими интервалами;
* превращать чтение и просмотр материалов в активное обучение;
* проверять recall, understanding и application;
* сохранять историю реального обучения;
* организовывать интервальные повторения;
* выбирать разумное следующее действие;
* возвращаться после длительных перерывов;
* хранить всё состояние в Git-репозитории.

---

# 2. Основные архитектурные принципы

## 2.1 One repository = one learning topic

Один репозиторий соответствует одной большой области обучения.

```text
system-design-learning/
electronics-learning/
english-learning/
```

Новые репозитории создаются из общего `learning-template`.

---

## 2.2 Repository is the source of truth

Внешняя БД для работы системы не требуется.

Репозиторий должен быть:

* самодостаточным;
* переносимым;
* читаемым человеком;
* восстанавливаемым из Git;
* пригодным для работы Codex;
* пригодным для будущего Web UI.

---

## 2.3 AI creates meaning, code manages state

Codex выполняет семантическую работу:

* onboarding;
* diagnostic;
* построение и развитие Knowledge Graph;
* создание Skeleton Units;
* инициализацию Unit;
* поиск материалов;
* генерацию адаптированных учебных материалов;
* формирование Study Focus;
* создание вопросов и практических заданий;
* анализ ответов;
* assessment;
* поиск gaps;
* предложение корректировок маршрута.

Scripts выполняют детерминированные операции:

* validation;
* проверку prerequisites;
* изменение Session state;
* расчёт review intervals;
* построение Progress;
* определение технически доступных Nodes;
* построение indexes;
* rebuild / repair.

Codex не должен вручную вычислять то, что может однозначно вычислить код.

---

# 3. Primary и Derived Data

Это главное разделение данных системы.

## PRIMARY

Первичные данные являются источником истины:

```text
context
graph
units
evidence
assessment-events
sessions
gaps
interests
generated-resources
```

Их потеря означает потерю информации.

## DERIVED

Производные данные:

```text
progress
frontier
indexes
```

Они существуют ради удобства и скорости.

Любой Derived-файл должен быть возможно удалить и построить заново из Primary Data.

Основной принцип:

```text
PRIMARY > DERIVED
```

---

# 4. Структура репозитория

```text
learning-topic/
├── learning.yaml
│
├── config/
│   ├── context.yaml
│   └── settings.yaml
│
├── map/
│   ├── graph.yaml
│   └── frontier.yaml
│
├── units/
│
├── evidence/
│
├── assessments/
│
├── sessions/
├── gaps/
├── interests/
│
├── resources/
│   └── generated/
│
├── progress/
│   └── units.yaml
│
├── indexes/
│
├── scripts/
├── .agents/
│   └── skills/
├── schemas/
│
├── agents/
│
└── docs/
    └── SPEC.md
```

`agents/` является опциональной папкой и может отсутствовать в первой реализации.

---

# 5. learning.yaml

Метаданные репозитория.

```yaml
format_version: 1

topic:
  id: system-design
  title: System Design

learning_core:
  version: 0.7.0

created_at: 2026-09-11
```

---

# 6. Context

`config/context.yaml` описывает, зачем конкретный пользователь изучает эту тему.

Например:

```yaml
goal:
  why: professional-growth

  outcome: >
    Уметь самостоятельно проектировать backend-системы
    и аргументировать архитектурные решения.

depth: working

constraints:
  default_session_minutes: 25
  sessions_per_week: 4

preferences:
  languages:
    - ru
    - en

  resources:
    - article
    - documentation
    - video
```

Context может изменяться.

Изменение цели:

```text
context changes
      ↓
history remains
      ↓
frontier recalculated
```

История значимых изменений Context должна сохраняться либо через Git history, либо отдельными events в будущих версиях.

---

# 7. Init

Основной сценарий создания учебного репозитория:

```text
init
```

Поток:

```text
topic
  ↓
goal
  ↓
context
  ↓
diagnostic
  ↓
initial graph
  ↓
initial frontier
  ↓
status
```

После `init` репозиторий должен быть готов к:

```text
session 25
```

---

# 8. Onboarding

Onboarding содержит примерно:

* 5–6 основных вопросов;
* до нескольких адаптивных уточнений.

Необходимо определить:

* зачем изучается тема;
* желаемый outcome;
* текущий опыт;
* желаемую глубину;
* типичный размер Session;
* предпочтения по материалам и формату обучения.

---

# 9. Diagnostic

Diagnostic нужен для первоначальной оценки уровня.

Он не считается полноценным доказательством mastery.

Основной принцип:

```text
Diagnostic = hypothesis
Evidence = confirmation
```

Diagnostic может маркировать области как:

```text
strong
weak
unknown
```

Если последующее Evidence противоречит Diagnostic, приоритет имеет Evidence.

В Stage 1 результат Diagnostic хранится как Primary Data в секции
`diagnostic` файла `config/context.yaml`. Он не создаёт Progress и не
подтверждает prerequisites.

---

# 10. Knowledge Graph

`map/graph.yaml` описывает предметную область.

Graph отвечает:

> Что существует внутри темы и как знания связаны между собой?

Graph не является курсом и не хранит пользовательский Progress.

---

# 11. Graph Node

Минимальные типы:

```text
area
topic
concept
```

Пример:

```text
Caching                       area
  Cache invalidation          topic
    Cache stampede            concept
```

Node:

```yaml
id: cache-stampede
title: Cache stampede
type: concept

summary: >
  Large number of concurrent requests reaching
  the source after cache miss or expiration.

importance: core

tags:
  - caching
  - reliability
```

---

# 12. Graph Edges

Минимальный набор:

```text
part-of
prerequisite
related
```

Пример:

```yaml
edges:
  - from: caching-basics
    to: cache-stampede
    type: prerequisite
```

Graph является графом, даже если UI позднее визуализирует его как Mind Map.

---

# 13. Graph Evolution

Knowledge Graph является изменяемым.

Codex может предложить:

* добавить Node;
* добавить Edge;
* изменить иерархию;
* изменить importance;
* признать Node устаревшим.

Основной принцип:

```text
Graph mutable
IDs durable
```

ID, на который уже ссылается Primary Data, нельзя переиспользовать для другого понятия.

Graph expansion is integration-first. При добавлении знаний:

* переиспользуются семантически подходящие существующие Nodes и ветки;
* расширение существующей ветки предпочтительнее параллельной иерархии;
* новый grouping Node должен добавлять реальную семантическую структуру, а не только объединять недавно запрошенные понятия;
* автоматически применяемый graph delta должен оставаться связанным с существовавшим до него Graph;
* новая disconnected или top-level ветка является structural change и требует явного семантического обоснования или подтверждения пользователя.

Несколько самостоятельных top-level areas допустимы. Ограничение на автоматическое применение относится к эволюции Graph, а не к его глобальной форме.

---

# 14. Deprecated Node

Если первоначальная модель оказалась неправильной:

```yaml
id: consistency
status: deprecated

replaced_by:
  - consistency-models
  - consistency-guarantees
```

Старые Unit и Evidence продолжают ссылаться на старый ID.

История не переписывается.

---

# 15. Unit

Graph Node отвечает:

> Что нужно знать?

Unit отвечает:

> Какое конкретное учебное действие мы выполняем?

Целевой размер:

```text
20–30 минут
```

Это ориентир, а не ограничение.

Unit может занимать несколько Sessions.

---

# 16. Unit ↔ Graph

Unit ссылается на один или несколько Nodes:

```yaml
nodes:
  - consistency
  - replication
  - quorum
```

Связь many-to-many.

Один Node может иметь несколько Unit.

Одна интеграционная Unit может затрагивать несколько Nodes.

Обратная связь:

```text
Node → Units
```

вычисляется через Index и не дублируется в Graph.

---

# 17. Hybrid Unit Materialization

Unit создаётся в два этапа.

## Skeleton Unit

Лёгкая заготовка:

```yaml
id: quorum-reads-writes
title: Quorum reads and writes

goal: >
  Understand quorum and basic trade-offs.

estimated_minutes: 25

nodes:
  - quorum
  - replication
```

Skeleton обычно существует внутри Frontier.

## Initialized Unit

Перед изучением Codex учитывает:

* Context;
* relevant Graph;
* prerequisites;
* Diagnostic;
* Progress;
* relevant Evidence;
* Session time budget.

После этого создаётся полноценная Unit с:

* точной целью;
* concepts;
* Study Focus;
* practice requirements;
* verification criteria.

---

# 18. Unit Lifecycle

Учебное состояние Unit:

```text
draft
  ↓
ready
  ↓
initialized
  ↓
learning
  ↓
practice
  ↓
verified
```

Возможны возвраты:

```text
verified → practice
verified → learning
practice → learning
```

Цикл интервальных повторений не является состоянием освоения Unit.
Он хранится независимо в `Progress.review`; наступление due-даты не меняет
`status`, а результат Review может изменить его.

Важно:

```text
paused
```

**не является состоянием Unit.**

Pause относится исключительно к Session.

---

# 19. Multi-session Unit

Если времени не хватило, Unit не разбивается автоматически.

Логическая Session создаёт checkpoint и может продолжаться через несколько
временных segments. Resume сохраняет Session ID и продолжает ту же Unit.

```text
Unit: learning

Segment A
   ↓
checkpoint
   ↓
Segment B
   ↓
continue Unit
```

Если Unit систематически оказывается существенно больше планируемого размера, можно установить:

```yaml
size_warning: true
```

Автоматического Unit splitting в MVP нет.

---

# 20. Resources

Resource является заменяемым инструментом.

Основной принцип:

```text
Unit = what we learn
Resource = how we learn it this time
```

Перед подготовкой материала пользователь выбирает Study Mode для текущей
Session/попытки:

```text
external
generated
hybrid
```

Study Mode не является свойством Unit: одна Unit в разных попытках может
изучаться по-разному. Codex может кратко рекомендовать режим, но выбор остаётся
за пользователем.

Каноническая Resource-модель разделяет происхождение и формат:

```yaml
type: external | generated
format: article | documentation | video | course | book | interactive
```

`external` использует найденный внешний материал. `generated` использует
адаптированную к Unit и контексту пользователя учебную статью. `hybrid`
содержит два независимых Resource — внешний и сгенерированный — в выбранном
пользователем порядке; сгенерированный материал не является автоматическим
summary внешнего.

Generated Resource хранится целиком в `resources/generated/<resource-id>.md`
со стабильным ID и YAML frontmatter. Это Primary Data: rebuild не генерирует,
не заменяет и не переписывает такие документы. Внешние статьи целиком в
repository не копируются. Источники, использованные для проверки generated
статьи, записываются в её frontmatter и не смешиваются с external Resource,
который непосредственно изучал пользователь.

При инициализации Codex предлагает обычно 2–3 варианта.

Для каждого показываются:

* формат;
* язык;
* примерная длительность;
* уровень;
* причина выбора.

Если Resource:

* оказался плохим;
* слишком сложным;
* перестал существовать;

его можно заменить без изменения Unit.

Фактически использованные Resources записываются в порядке изучения в
Session/Evidence. Отклонённые до начала изучения варианты в историю не входят.

---

# 21. Study Focus

Перед началом материала Codex формирует 2–3 вопроса.

Например:

```text
Что гарантирует R + W > N?

Как увеличение R влияет на latency?

Как увеличение W влияет на availability?
```

Study Focus должен превращать пассивное чтение в направленное изучение.

---

# 22. Learning Cycle

```text
Skeleton
   ↓
Initialize
   ↓
Study Mode Selection
   ↓
Resource Preparation
   ↓
Study Focus
   ↓
Study
   ↓
Optional Discussion
   ↓
Active Recall
   ↓
Practice
   ↓
Evidence
   ↓
Assessment
   ↓
Progress Update
   ↓
Review Scheduling
```

Просмотр материала и Discussion сами по себе не подтверждают mastery.
Discussion относится к поддерживаемому Study, а не к Assessment. Значимый
разговор может оставить компактный `discussion_summary` в Session с вопросами,
уточнениями, misconceptions, possible Gaps, явно выраженными Interests и
`assessment_focus`, но не transcript. Он не создаёт Evidence, не обновляет
Progress и не подтверждает Gap. Возможная слабость становится Gap только через
последующие независимые Recall/Practice, Evidence и Assessment.

---

# 23. Missing Prerequisite

Если в процессе Unit обнаруживается реальный пробел:

```text
current Unit
    ↓
missing prerequisite detected
    ↓
pause Session
    ↓
create prerequisite Skeleton
    ↓
raise priority
    ↓
study prerequisite
    ↓
later return to original Unit
```

Это не считается неудачной попыткой.

---

# 24. Evidence

Evidence — неизменяемый факт учебной попытки.

Пример структуры:

```text
evidence/
└── quorum-reads-writes/
    ├── 2026-09-11-initial.yaml
    ├── 2026-09-15-review.yaml
    └── 2026-09-29-review.yaml
```

Evidence содержит:

* Unit ID;
* тип попытки;
* prompt;
* answer;
* takeaways пользователя;
* обнаруженные raw observations;
* упорядоченный список фактически использованных Resources;
* ссылки на Session.

После создания Evidence не изменяется.

Новая форма использует `resources[]`. Исторический одиночный `resource` остаётся
валидным без миграции; новые записи используют `type` для происхождения и
`format` для формата.

---

# 25. Assessment

Assessment — интерпретация Evidence.

Минимальные измерения:

```text
recall
understanding
application
```

Например:

```yaml
recall: good
understanding: good
application: hard

gaps:
  - >
    Understands quorum but struggles to select
    R/W for availability requirements.
```

Assessment не является частью неизменяемого Evidence.

---

# 26. Assessment Events

Assessment хранится отдельно:

```text
assessments/
└── <evidence-id>/
    ├── 001.yaml
    └── 002.yaml
```

Первоначальная оценка:

```yaml
id: assessment-001
evidence: evidence-id
type: initial
created_at: ...

result:
  recall: good
  understanding: good
  application: hard

evaluated:
  recall:
    nodes: [quorum]
  understanding:
    nodes: [quorum]
  application:
    nodes: [quorum]
```

`result` хранит полное текущее mastery state и может включать перенесённые из предыдущей Assessment значения. `evaluated` содержит только dimensions и Graph Nodes, реально проверенные текущей Evidence; только они могут создавать или обновлять Gap signals. Старые Assessment без `evaluated` остаются валидными, но не используются для новой Gap attribution.

`unit.nodes` задаёт формальную границу Assessment для Unit. Каждый Graph Node,
указанный в `Assessment.evaluated`, должен присутствовать в `unit.nodes` исходного
Unit, на который ссылается Evidence. Assessment может обновлять Progress или
состояние подтверждённого Gap только для таких узлов. Если Assessment формально
оценивает хотя бы один узел вне этой границы, всё обновление отклоняется до
изменения Derived State.

Наблюдения об узлах вне `unit.nodes` могут сохраняться только как неподтверждённые
гипотезы или сигналы — например, `possible_gaps`, `assessment_focus` или notes.
Они не меняют Progress, не создают и не подтверждают Gap и не считаются
формальной оценкой, пока не будут проверены через Unit, который объявляет эти
узлы в `unit.nodes`.

Если оценка пересмотрена:

```yaml
id: assessment-002
evidence: evidence-id

type: reevaluation
supersedes: assessment-001
reason: user_request

result:
  recall: good
  understanding: good
  application: good
```

Старая Assessment не удаляется.

---

# 27. Assessment Principle

```text
Evidence immutable
Assessment append-only and revisable
Progress rebuildable
```

Active Assessment определяется детерминированно по цепочке supersedes.

## Assessment Reevaluation

Reevaluation является явным действием и никогда не запускается автоматически.
Допустимые причины:

```text
user_request
contradiction
rubric_change
```

Codex может предложить пересмотр, но для записи нового event требуется явно
выбранное действие reevaluation. Оно повторно интерпретирует только исходный
Evidence. Более поздние ответы, другие Evidence, chat memory и Session summary
могут быть причиной начать пересмотр, но не являются материалом для оценки.

Цепочка `supersedes` всегда линейна:

```text
A → B → C
```

Self-reference, cycles, branching, cross-Evidence links и superseding уже
superseded Assessment запрещены. Для каждого Evidence, у которого есть
Assessment, существует ровно один active Assessment: единственный event, на
который не ссылается `supersedes` следующего event. Исторические Assessments
остаются на диске.

Переоценка проходит тот же формальный `unit.nodes` boundary, что и исходная
Assessment. Перед записью deterministic core полностью проверяет новый event и
проектируемые изменения. Затем одной логической операцией:

```text
append Assessment
→ rebuild Progress
→ reconcile Gaps
→ rebuild Frontier routing
```

При ошибке ни один из этих результатов не должен остаться частично применённым.
Reevaluation не создаёт Evidence или Session и не увеличивает число attempts,
Practice или Review.

---

# 28. Progress

`progress/units.yaml` является агрегированным Derived State.

Например:

```yaml
quorum-reads-writes:

  status: verified

  mastery:
    recall: good
    understanding: good
    application: good

  attempts: 2

  last_attempt: 2026-09-11

  review:
    due: 2026-09-15
    interval_days: 4
    repetitions: 1
```

Progress можно удалить и пересчитать.

При rebuild для каждого Evidence участвует только его active Assessment.
Superseded Assessments не влияют на текущее mastery, но сохраняются для аудита.

## Gap provenance after reevaluation

Gap signals являются исторической Primary Data и не удаляются. Signal считается
active только когда его `assessment` является active Assessment для указанного
Evidence. Сигналы superseded Assessments остаются provenance, но не участвуют в
текущем Gap state.

Gap поддерживает состояния:

```text
detected
confirmed
resolved
invalidated
```

`resolved` означает, что реальная слабость была исправлена последующим
обучением. `invalidated` означает, что слабость существовала только из-за
интерпретации Assessment, которая затем была superseded. Эти состояния не
взаимозаменяемы.

Reconciliation по active signals может понизить `confirmed` до `detected`,
перевести `detected`/`confirmed` в `invalidated` или переоткрыть `resolved` как
`detected`/`confirmed`. Каждый reevaluation-driven переход записывается в
`Gap.history` с новым Assessment и `reason: reevaluation`. Invalidated Gap не
участвует в Frontier routing.

---

# 29. Frontier

`map/frontier.yaml` — Derived State.

Frontier содержит разумные следующие учебные действия примерно на 5–10 Sessions.

Он не является строгой очередью.

---

# 30. Multiple Learning Branches

Frontier может содержать несколько направлений:

```yaml
focus:
  primary: consistency

  secondary:
    - caching
    - system-design-practice
```

Primary Focus удерживает общий маршрут.

Secondary Focus позволяет:

* заниматься практикой;
* возвращаться к старым областям;
* менять тип активности;
* использовать текущий интерес.

---

# 31. Frontier Generation

```text
Graph
+
Progress
+
Context
+
Diagnostic
+
Gaps
      ↓
technical candidates
      ↓
Codex prioritization
      ↓
Skeleton Units
      ↓
Frontier
```

Scripts определяют:

* какие Nodes доступны;
* какие prerequisites выполнены;
* какие области уже достаточно покрыты;
* какие Units активны.

Codex решает:

* чему сейчас педагогически полезнее уделить внимание;
* какие Skeleton Units создать;
* какой Focus выбрать.

---

# 32. User Override

Frontier — рекомендация, а не запрет.

Пользователь может сказать:

> Сегодня хочу изучить X.

Если prerequisites отсутствуют, система предупреждает и предлагает:

* сначала prerequisite;
* продолжить несмотря на рекомендацию.

Окончательный выбор остаётся за пользователем.

---

# 33. Session

Session — один логический учебный процесс от начала до завершения. Фактические
заходы хранятся как `segments`; у каждого есть свой budget, `started_at` и
`ended_at`. Активное время является суммой закрытых segments.

В одном learning repository может существовать не более одной Session со
статусом `active` или `paused`.

Session может включать:

* Review;
* продолжение Unit;
* новую Unit;
* Practice;
* Integration Exercise.

Для Study Session дополнительно хранит выбранный `study.mode`, фактически
использованные `study.resources[]` и необязательный компактный
`study.discussion_summary`. Resource-кандидаты и полный Study transcript в
Session не сохраняются.

---

# 34. Session State

Session имеет состояния:

```text
active
paused
completed
```

`paused` существует только здесь.

Unit при этом остаётся, например:

```text
learning
```

---

# 35. Session Workflow

Главный пользовательский сценарий:

```text
session 25
```

или естественная фраза:

> У меня есть 25 минут.

Процесс:

```text
check active/paused Session
        ↓
check inactivity
        ↓
get due Reviews
        ↓
calculate Review budget
        ↓
inspect Frontier
        ↓
create plan
        ↓
perform learning
        ↓
create Evidence
        ↓
create Assessment
        ↓
update Derived State
        ↓
complete or pause Session
```

---

# 36. Session Plan

Session хранит:

```text
planned work
actual work
```

Например:

```text
planned:
  review cache-invalidation
  study cache-stampede

actual:
  review cache-invalidation: completed
  study cache-stampede: in_progress
```

Изменение плана является нормальным.

---

# 37. Pause / Checkpoint

При паузе Session сохраняет checkpoint:

```yaml
status: paused

checkpoint:
  updated_at: 2026-09-15T10:12:00+05:00
  unit: quorum-reads-writes
  action: study
  stage: study

  completed_steps:
    study_focus_shown: true
    study_completed: false

  study_mode: hybrid

  resources:
    - type: external
      format: documentation
      title: Quorum documentation
      url: https://example.com/quorum
      language: en
      status: completed

    - type: generated
      format: article
      id: resource-quorum-20260919-001
      path: resources/generated/resource-quorum-20260919-001.md
      title: Quorum reads and writes
      status: selected

  note: >
    Stopped after section about write quorum.
```

Checkpoint обновляется после выбора Resource, показа Study Focus, завершения
Study, каждого содержательного ответа в Recall/Practice, завершения этих
этапов и любого изменения action/stage. Он хранит только минимальное состояние
возобновления, а не transcript.

Checkpoint сохраняет Study Mode, порядок Resources, completion state каждого
из них и компактный DiscussionSummary. Resume пропускает завершённые Resources
и всегда переиспользует уже созданный generated Resource по сохранённым ID/path;
автоматическая повторная генерация запрещена. Это поддерживает оба hybrid
порядка и паузу между двумя материалами.

Pause не создаёт Evidence и не влияет на mastery. Budget является ориентиром
для planner и сам по себе не закрывает segment и не ставит Session на паузу.

---

# 38. Unexpected Interruption

Если терминал или процесс завершились аварийно, Session может остаться `active`.
Любая active Session, найденная при новом запуске или команде `session`/`status`,
считается потенциально stale; временной порог не используется.

Следующая команда `session` должна:

1. обнаружить старую active Session;
2. предложить восстановление;
3. закрыть прерванный segment временем последнего checkpoint;
4. открыть новый segment с новым budget и продолжить ту же Session.

Если checkpoint отсутствует, система не придумывает состояние и запрашивает у
пользователя только минимальные смысловые сведения о месте остановки, но не
просит оценить elapsed time. Прерванный segment закрывается консервативно по
его `started_at`, новый segment открывается в момент recovery, и только в него
записывается reconstructed checkpoint.

---

# 39. Review

Review создаёт новое Evidence.

Review не перезаписывает старую попытку.

Вопрос или Scenario должны отличаться от первоначальных.

Codex учитывает предыдущие gaps.

---

# 40. Review Budget

Review не должен захватывать всю Session.

Ориентир:

```text
20–30% Session budget
```

Это configurable setting.

Накопившиеся Review распределяются между Sessions.

---

# 41. Spaced Repetition

Для MVP достаточно результатов:

```text
failed
hard
good
easy
```

На их основании Scripts вычисляют следующий interval.

Сложные алгоритмы вроде FSRS не входят в первую реализацию.

---

# 42. Long Inactivity

После длительного перерыва backlog Review не считается долгом.

Система запускает Recalibration.

```text
long inactivity
      ↓
select representative knowledge
      ↓
short diagnostic reviews
      ↓
new Evidence
      ↓
update Progress
      ↓
rebuild Frontier
      ↓
resume learning
```

Конкретный порог inactivity является configurable.

---

# 43. Status

Основной внешний сценарий:

```text
status
```

Он должен быстро отвечать:

1. Где я сейчас?
2. Что требует внимания?
3. Что доступно дальше?
4. Есть ли незавершённая Session?

Пример:

```text
System Design

Verified: 18
Practice: 3
Reviews due: 2

Primary focus:
Consistency

Needs attention:
Cache invalidation — application weak

Frontier:
1. Quorum reads/writes — 25 min
2. Read-after-write consistency — 20 min

Paused:
none
```

Фактические данные предоставляет Script.

Codex может добавить краткую интерпретацию.

---

# 44. Indexes

`indexes/` содержит только Derived Data.

Примеры:

```text
Node → Units
Unit → latest Evidence
Evidence → active Assessment
due Reviews
weak Nodes
active Units
```

Indexes существуют, чтобы Codex не анализировал весь репозиторий.

---

# 45. Local Working Context

Codex по умолчанию не должен загружать всю историю.

Обычно ему нужны:

```text
Context
relevant Graph fragment
Frontier
relevant Progress
latest/relevant Evidence
active Assessment
current Session
```

Принцип:

> History may grow indefinitely. Working context should remain small.

---

# 46. Rebuild

Derived State должен иметь команды восстановления.

Минимально:

```text
rebuild progress
rebuild frontier
rebuild indexes
```

Они используют Primary Data.

---

# 47. Repair

Отдельные операции могут понадобиться для исправления технических состояний:

```text
repair session-state
validate repository
```

Scripts должны по возможности быть idempotent.

Повторный запуск не должен создавать дубликаты Primary Events.

---

# 48. Partial Failure

Пример:

```text
Evidence successfully written
Assessment written
Progress update failed
```

После восстановления:

```text
rebuild progress
```

возвращает систему в согласованное состояние.

Primary Data всегда важнее Derived State.

---

# 49. Main External UX

Для пользователя MVP должен оставаться простым.

Основные действия:

```text
init
session [minutes]
status
```

Большинство операций доступны и естественным языком.

Например:

```text
Хочу изучать System Design.

У меня есть 20 минут.

Что у меня сейчас по прогрессу?

Давай остановимся здесь.

Сегодня хочу разобраться с Kafka.
```

---

# 50. Internal Operations

Пользователь обычно не вызывает напрямую:

```text
initialize-unit
create-evidence
create-assessment
calculate-review
update-progress
build-indexes
build-frontier
repair
```

Эти операции используются Skills/Core.

---

# 51. Skills

Предварительный набор:

```text
topic-onboarding
diagnostic

build-learning-map
evolve-learning-map

build-frontier

initialize-unit
find-resources

run-study
assess-answer
reevaluate-assessment

run-review
run-recalibration

run-session
status
```

Количество Skills может быть уменьшено при реализации, если некоторые удобно объединить.

---

# 52. Agents

Multi-agent architecture не является требованием MVP.

Предпочтительная первая версия:

```text
Codex
+
Skills
+
Scripts
```

Отдельные Agents вводятся только после появления реальной необходимости.

---

# 53. Learning Template / Core

Чистый template содержит:

```text
.agents/skills/
scripts/
schemas/
docs/
default config/
```

Пользователь создаёт из него новый репозиторий для конкретной темы.

Каждый topic repository хранит Core version:

```yaml
learning_core:
  version: 0.7.0
```

Обновление существующих репозиториев на новую версию Core не входит в MVP.

---

# 54. Web UI

Web UI не входит в MVP.

В будущем он должен читать существующую файловую модель и не становиться новым Source of Truth.

Возможные представления:

* Knowledge Graph;
* Node → Units;
* mastery overlay;
* coverage;
* Frontier;
* Primary / Secondary Focus;
* Reviews;
* Evidence history;
* Session history;
* weak areas.

---

# 55. Core Invariants

1. Один repository = одна большая learning topic.
2. Primary Data является источником истины.
3. Derived Data можно пересоздать.
4. Graph не хранит пользовательский Progress.
5. Unit не является Graph Node.
6. Unit явно ссылается на Graph Nodes.
7. Graph mutable.
8. Использованные IDs durable.
9. Diagnostic является гипотезой.
10. Evidence является неизменяемым фактом попытки.
11. Assessment хранится отдельно от Evidence.
12. Assessment может быть переоценён через новый event.
13. Старые Assessments не удаляются.
14. Progress rebuildable.
15. Frontier rebuildable.
16. Indexes rebuildable.
17. Resource является заменяемым инструментом.
18. Просмотр Resource не подтверждает mastery.
19. Unit может занимать несколько Sessions.
20. `paused` относится только к Session.
21. Pause не влияет на mastery.
22. Automatic Unit Split отсутствует в MVP.
23. Frontier является рекомендацией.
24. User Override разрешён.
25. Review имеет ограниченный time budget.
26. Overdue Review не является долгом.
27. После долгого перерыва используется Recalibration.
28. Context может меняться без переписывания HISTORY.
29. Codex работает преимущественно с локальным контекстом.
30. Детерминированное состояние управляется Scripts.
31. Семантические решения выполняет Codex.
32. Partial failure не должен приводить к потере Primary Data.
33. Репозиторий должен быть полностью пригоден для работы без Web UI.
34. Study Mode относится к попытке, а не к Unit.
35. Generated Resource является неизменяемым Primary Data.
36. Discussion не является Evidence или Assessment.
37. Исторические одиночные `resource` остаются валидными без миграции.

---

# 56. Non-goals MVP

В MVP намеренно не входят:

* Web UI;
* мобильное приложение;
* серверная БД;
* multi-repository dashboard;
* сложная multi-agent architecture;
* FSRS;
* автоматическое обновление Learning Core;
* автоматический Unit splitting;
* gamification;
* achievements;
* social features;
* сложная productivity analytics.

---

# 57. Implementation Strategy

Спецификация описывает целевую модель MVP, но первая реализация не должна пытаться реализовать всё одновременно.

Первый вертикальный срез:

```text
init
 ↓
graph
 ↓
frontier
 ↓
session
 ↓
Unit
 ↓
Evidence
 ↓
Assessment
 ↓
Progress
 ↓
status
```

На этом этапе система уже должна позволять реально начать изучать `System Design`.

После проверки вертикального среза добавляются:

```text
Reviews
Pause / Resume
Rebuild
Graph Evolution
Recalibration
Assessment Reevaluation
Indexes optimisation
```

---

# 58. Главный критерий успеха MVP

MVP считается успешным не потому, что реализованы все сущности спецификации.

Он успешен, если на реальной теме пользователь может:

```text
создать учебный репозиторий
        ↓
получить разумную карту
        ↓
провести короткую Session
        ↓
реально что-то изучить
        ↓
пройти проверку
        ↓
сохранить Evidence
        ↓
вернуться через несколько дней
        ↓
продолжить с правильного места
```

Главная проверяемая гипотеза:

> Такая система помогает регулярно учиться короткими сессиями, меньше потреблять информацию пассивно, лучше удерживать изученное и постепенно превращать отдельные знания в практическое понимание.
