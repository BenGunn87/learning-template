# Stage 1 — Bootstrap + Init

## 1. Цель этапа

Создать базовый `learning-template`, из которого можно создать новый репозиторий для изучения одной большой темы и выполнить первичную инициализацию обучения.

После завершения Stage 1 пользователь должен иметь возможность:

```text
создать репозиторий из template
        ↓
сообщить тему обучения
        ↓
пройти onboarding
        ↓
пройти короткую диагностику
        ↓
получить context.yaml
        ↓
получить первоначальный graph.yaml
        ↓
получить frontier.yaml с 5–10 Skeleton Units
        ↓
посмотреть первоначальный status
```

На этом этапе пользователь ещё не проходит полноценные учебные Unit.

---

# 2. Архитектурная основа

Перед реализацией необходимо прочитать:

```text
docs/SPEC.md
```

Основные обязательные принципы:

* one repository = one learning topic;
* repository является source of truth;
* Primary Data и Derived Data разделены;
* Codex отвечает за семантические решения;
* scripts отвечают за детерминированные операции;
* Graph не содержит пользовательский Progress;
* Unit не является Graph Node;
* Frontier является Derived Data;
* Graph mutable, IDs durable;
* Diagnostic является гипотезой, а не подтверждённым mastery.

Если техническое решение противоречит `SPEC.md`, приоритет имеет `SPEC.md`.

---

# 3. Начальная структура template

Создать примерно такую структуру:

```text
learning-template/
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
├── evidence/
├── assessments/
├── sessions/
├── progress/
├── indexes/
│
├── scripts/
├── .agents/
│   └── skills/
├── schemas/
│
└── docs/
    └── SPEC.md
```

Пустые runtime-каталоги допускается сохранять через `.gitkeep`.

`agents/` на Stage 1 не требуется.

---

# 4. Template State

До выполнения `init` template не должен содержать конкретную учебную тему.

Например `learning.yaml` может содержать:

```yaml
format_version: 1

topic: null

learning_core:
  version: 0.3.0
```

После `init` тема заполняется.

---

# 5. Settings

Создать `config/settings.yaml` с минимальными настройками.

Пример:

```yaml
session:
  default_minutes: 25

frontier:
  target_units: 7
  min_units: 5
  max_units: 10

diagnostic:
  enabled: true
```

Не добавлять настройки, которые пока не используются Stage 1.

---

# 6. Schemas

Создать схемы для структур, реально используемых Stage 1:

```text
learning
context
graph
frontier
```

Схемы должны позволять scripts валидировать generated YAML.

Предпочтение следует отдавать простым, читаемым форматам.

Не проектировать заранее схемы Evidence, Assessment и Session глубже, чем необходимо для структуры репозитория.

---

# 7. Init UX

Пользовательский сценарий должен поддерживать естественную команду вроде:

> Хочу изучать System Design.

или явный сценарий `init`.

Codex должен определить, что репозиторий ещё не инициализирован, и запустить onboarding.

Повторный `init` поверх уже инициализированного репозитория не должен молча перезаписывать данные.

---

# 8. Onboarding

Создать Skill для onboarding.

Он должен выяснить минимум:

1. Какую тему пользователь хочет изучать.
2. Зачем он её изучает.
3. Какой результат хочет получить.
4. Как оценивает свой текущий опыт.
5. Какую глубину изучения хочет.
6. Сколько времени обычно доступно на одну Session.
7. Какие форматы материалов предпочитает.
8. Какие языки материалов допустимы.

Не обязательно задавать все вопросы, если ответ уже известен из предыдущего сообщения.

Не превращать onboarding в длинную анкету.

Ориентир:

```text
5–6 основных вопросов
+
до нескольких адаптивных
```

---

# 9. Context Generation

По результатам onboarding создать:

```text
config/context.yaml
```

Пример структуры:

```yaml
goal:
  why: professional-growth

  outcome: >
    Уметь самостоятельно проектировать backend-системы
    и аргументировать архитектурные решения.

depth: working

constraints:
  default_session_minutes: 25

preferences:
  languages:
    - ru
    - en

  resources:
    - article
    - documentation
    - video

diagnostic:
  status: completed
```

Не хранить в Context данные, которые относятся к Knowledge Graph или Progress.

---

# 10. Diagnostic

После onboarding провести короткую первичную диагностику.

Цель диагностики:

* определить уже знакомые области;
* найти заметные gaps;
* определить примерную глубину стартового маршрута.

Diagnostic не должен быть экзаменом.

Для большой темы следует проверить несколько репрезентативных областей, а не пытаться проверить всё.

Результаты могут иметь состояния:

```text
strong
weak
unknown
```

Результат диагностики сохранить как часть Primary Data.

На Stage 1 результат хранится в секции `diagnostic` файла
`config/context.yaml`; отдельная сущность Diagnostic пока не вводится.

Не превращать Diagnostic автоматически в Verified Progress.

---

# 11. Initial Knowledge Graph

После Context и Diagnostic Codex создаёт первоначальный:

```text
map/graph.yaml
```

Graph должен содержать:

```text
area
topic
concept
```

и связи:

```text
part-of
prerequisite
related
```

Пример:

```yaml
nodes:
  - id: caching
    title: Caching
    type: area

  - id: cache-invalidation
    title: Cache invalidation
    type: topic

  - id: cache-stampede
    title: Cache stampede
    type: concept

edges:
  - from: cache-invalidation
    to: caching
    type: part-of

  - from: caching-basics
    to: cache-stampede
    type: prerequisite
```

---

# 12. Graph Generation Rules

Первоначальный Graph не должен пытаться полностью разложить тему до атомарного уровня.

Нужно:

* покрыть основные области темы;
* дать достаточно структуры для понимания направления;
* подробно раскрыть только ближайшие важные участки;
* учитывать Context;
* учитывать Diagnostic;
* использовать устойчивые machine-readable IDs.

Не создавать Progress внутри Graph.

---

# 13. Graph Validation

Создать script, который проверяет минимум:

* уникальность Node IDs;
* существование Nodes, используемых в Edges;
* допустимые Node types;
* допустимые Edge types;
* отсутствие self-reference там, где она бессмысленна;
* корректный YAML/schema.

Например внутренне это может быть операция:

```text
validate graph
```

Пользователь не обязан вызывать её напрямую.

---

# 14. Initial Frontier

После Graph сформировать:

```text
map/frontier.yaml
```

Frontier должен содержать примерно 5–10 Skeleton Units.

Пример:

```yaml
focus:
  primary: consistency
  secondary:
    - caching

units:
  - id: consistency-models
    title: Strong vs eventual consistency

    nodes:
      - consistency

    goal: >
      Уметь объяснить основные различия и выбрать
      подходящую модель для простого сценария.

    estimated_minutes: 25

    priority: high

  - id: quorum-basics
    title: Quorum reads and writes

    nodes:
      - quorum
      - replication

    goal: >
      Понять R/W/N и базовые trade-offs.

    estimated_minutes: 25
```

---

# 15. Skeleton Unit Rules

Skeleton Unit должна содержать только данные, необходимые для планирования.

Минимально:

```text
id
title
nodes
goal
estimated_minutes
priority
```

При необходимости:

```text
blocked_by
```

Не генерировать на Stage 1:

* Study Focus;
* Resources;
* Practice;
* Verification;
* Assessment.

Это относится к следующему этапу.

---

# 16. Frontier Logic

Scripts должны помочь определить техническую доступность кандидатов.

Codex отвечает за педагогическую приоритизацию.

На Stage 1 допускается простой алгоритм.

Важно сохранить разделение:

```text
scripts:
  can this be studied?

Codex:
  is this worth studying now?
```

---

# 17. Frontier as Derived Data

`frontier.yaml` является Derived State.

Необходимо предусмотреть внутреннюю возможность пересоздать его из:

```text
context
+
graph
+
diagnostic
```

Полноценный `rebuild frontier` может быть минимальным на Stage 1, но архитектура не должна делать Frontier единственным источником данных.

---

# 18. Initial Status

После успешного `init` показать краткий статус.

Например:

```text
System Design

Goal:
Professional backend growth

Diagnostic:
Strong:
- database basics
- basic caching

Weak:
- consistency

Unknown:
- consensus

Primary focus:
Consistency

Frontier:
1. Consistency models — 25 min
2. Replication basics — 25 min
3. Quorum reads/writes — 25 min
...
```

Status должен строиться из файлов репозитория, а не только из памяти текущего разговора.

---

# 19. Scripts Stage 1

Реализовать только минимально необходимые deterministic scripts.

Ожидаемые возможности:

```text
validate repository
validate graph
validate frontier
detect initialized state
build basic frontier candidates
render/read basic status
```

Названия и язык реализации можно выбрать самостоятельно.

Не реализовывать большую CLI-платформу ради будущих возможностей.

---

# 20. Skills Stage 1

Репозиторные Skills размещаются в `.agents/skills/`, чтобы Codex автоматически обнаруживал их при открытии repository.

Минимально нужны Skills:

```text
topic-onboarding
diagnostic
build-learning-map
build-frontier
status
```

Допускается объединение Skills, если это делает систему проще.

Skills должны:

* читать `SPEC.md`;
* использовать repository files как состояние;
* не полагаться на память предыдущих чатов;
* вызывать deterministic scripts там, где это возможно.

---

# 21. Не реализовывать на Stage 1

Не реализовывать:

```text
полноценные Sessions
Unit initialization
Resource search workflow
Study Focus
Practice
Evidence
Assessment
Progress mastery
Reviews
Spaced repetition
Pause / Resume
Recalibration
Assessment reevaluation
Web UI
Multi-agent architecture
Learning Core upgrade
```

Папки для будущих сущностей могут существовать, но логика не должна реализовываться заранее.

---

# 22. Error Handling

Минимально обработать:

* повторный `init`;
* повреждённый YAML;
* невалидный Graph;
* Frontier со ссылкой на неизвестный Node;
* отсутствие обязательного Context;
* частично выполненный `init`.

Необходимо избегать молчаливой потери данных.

---

# 23. Idempotency

Повторная validation не должна изменять файлы.

Повторный запуск внутренних deterministic операций с тем же input должен приводить к тому же результату.

`init` не должен автоматически уничтожать уже существующую тему.

---

# 24. Human Readability

Все основные YAML-файлы должны оставаться понятными человеку.

Не хранить критическое состояние только в opaque generated IDs или бинарном формате.

Machine IDs должны быть стабильными и понятными:

```text
cache-stampede
quorum-reads-writes
eventual-consistency
```

а не:

```text
node-8f3a91
```

если нет технической необходимости.

---

# 25. Tests

Добавить автоматические тесты для deterministic части.

Минимум проверить:

* schema validation;
* duplicate Node ID;
* Edge на отсутствующий Node;
* invalid Node type;
* invalid Edge type;
* Frontier Unit с неизвестным Node;
* detection initialized/uninitialized repository.

AI-generated semantic quality автоматическими unit-тестами проверять не требуется.

---

# 26. Documentation

Добавить краткий `README.md`:

```text
что это за repository
как создать новую learning topic
как запустить init
какие файлы создаются
как посмотреть status
что пока не реализовано
```

`docs/SPEC.md` должен содержать полную архитектурную спецификацию v0.3.

---

# 27. Acceptance Criteria

Stage 1 считается завершённым, если можно выполнить реальный сценарий:

```text
1. Создать новый repository из learning-template.

2. Открыть его с Codex.

3. Сказать:
   "Хочу изучать System Design."

4. Пройти короткий onboarding.

5. Пройти короткую диагностику.

6. Получить валидный:
   config/context.yaml

7. Получить валидный:
   map/graph.yaml

8. Получить валидный:
   map/frontier.yaml

9. Frontier содержит 5–10 разумных Skeleton Units.

10. Graph и Frontier проходят deterministic validation.

11. Команда/запрос status читает состояние из repository
    и показывает первоначальный учебный маршрут.

12. Закрытие Codex и повторное открытие repository
    не приводит к потере контекста:
    система понимает тему исключительно по файлам repository.
```

---

# 28. Definition of Done

Stage 1 готов только тогда, когда его можно проверить не на synthetic fixture, а на настоящей теме:

```text
System Design
```

После этого не переходить автоматически к Stage 2.

Сначала необходимо использовать созданный repository, посмотреть на:

* качество onboarding;
* качество Diagnostic;
* качество Graph;
* полезность Frontier;
* удобство Status;
* размер и понятность файлов.

Только после этой проверки принимать решения о Stage 2.
