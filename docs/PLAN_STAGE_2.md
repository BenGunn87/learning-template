# Stage 2 — First Complete Learning Session

## 1. Цель

Реализовать первую полноценную учебную сессию поверх репозитория, уже инициализированного в Stage 1.

После Stage 2 пользователь должен иметь возможность сказать:

```text
У меня есть 25 минут
```

и пройти полный цикл:

```text
Frontier
   ↓
выбор Skeleton Unit
   ↓
инициализация Unit
   ↓
выбор Resource
   ↓
Study Focus
   ↓
изучение
   ↓
Active Recall
   ↓
Practice
   ↓
Evidence
   ↓
Assessment
   ↓
Progress
   ↓
Status
```

После закрытия Codex результат должен полностью сохраняться в repository.

---

# 2. Перед реализацией

Прочитать:

```text
docs/SPEC.md
```

Особенно разделы:

```text
Unit
Hybrid Unit Materialization
Resources
Study Focus
Learning Cycle
Evidence
Assessment
Progress
Session
Status
Primary / Derived Data
```

Stage 1 не должен быть сломан или существенно переработан без необходимости.

---

# 3. Scope

На Stage 2 реализуются:

```text
Session creation
Unit initialization
Resource selection
Study Focus
Active Recall
Practice
Evidence
Assessment
Progress
Status update
```

---

# 4. Не входит в Stage 2

Не реализовывать:

```text
Spaced repetition
Reviews
Review scheduling
Pause / Resume
Recalibration
Assessment reevaluation
Graph evolution
Missing prerequisite auto-routing
Rebuild / Repair
Advanced indexes
Web UI
Multi-agent architecture
```

Если обнаружен prerequisite gap, Codex может сообщить о нём пользователю, но полноценный workflow его автоматического добавления пока не нужен.

---

# 5. Main UX

Основной сценарий:

```text
session 25
```

или естественный язык:

```text
У меня есть 25 минут.
Давай позанимаемся.
Хочу продолжить System Design.
```

Codex должен сам понять, что необходимо запустить учебную Session.

Пользователь не должен вручную вызывать:

```text
initialize-unit
create-evidence
create-assessment
update-progress
```

---

# 6. Session Start

Перед началом Session система должна прочитать состояние repository:

```text
learning.yaml
config/context.yaml
map/graph.yaml
map/frontier.yaml
progress/
```

Если repository не инициализирован:

```text
не начинать Session
предложить init
```

Если всё корректно — создать Session.

---

# 7. Session File

Создать Primary Data:

```text
sessions/
  <session-id>.yaml
```

Session ID должен быть стабильным и уникальным.

Например:

```text
2026-09-14-001
```

Минимальная структура:

```yaml
id: 2026-09-14-001

started_at: ...

time_budget_minutes: 25

status: active

plan:
  unit: define-problem-and-requirements

actual:
  unit: null

evidence: []

completed_at: null
```

На Stage 2 Session поддерживает минимум:

```text
active
completed
```

Pause workflow пока не реализовывать.

---

# 8. Unit Selection

Система должна выбрать подходящую Skeleton Unit из:

```text
map/frontier.yaml
```

При выборе учитывать минимум:

```text
availability
priority
primary focus
time budget
existing Progress
```

Codex может рекомендовать Unit пользователю.

Если есть несколько разумных вариантов, допустимо показать 2–3.

Например:

```text
У тебя 25 минут.

Предлагаю:

1. Define problem and requirements — 25 min
2. Estimate workload — 20 min
3. Trace request lifecycle — 25 min
```

Пользователь может выбрать другой вариант.

Frontier остаётся рекомендацией.

---

# 9. Initialized Unit

После выбора Skeleton Unit создать:

```text
units/<unit-id>.yaml
```

Initialized Unit должна быть значительно конкретнее Skeleton.

Минимальная структура:

```yaml
id: define-problem-and-requirements

title: Define problem and requirements

nodes:
  - design-process
  - requirements

goal: >
  Уметь начать System Design задачу с определения
  functional/non-functional requirements и основных constraints.

estimated_minutes: 25

concepts:
  - functional requirements
  - non-functional requirements
  - constraints
  - scope
  - assumptions

study_focus:
  - ...
  - ...
  - ...

practice:
  type: scenario
  goal: ...

verification:
  recall:
    enabled: true

  understanding:
    enabled: true

  application:
    enabled: true
```

Unit является Primary Data.

---

# 10. Unit Validation

Добавить schema и deterministic validation для Unit.

Проверять минимум:

```text
unique/stable id
known graph nodes
goal exists
estimated_minutes > 0
concepts not empty
2–3 Study Focus questions
practice exists
verification exists
```

Unit не должна содержать:

```text
mastery
next_review
user progress
assessment result
```

---

# 11. Resource Search

После инициализации Unit Codex должен найти 2–3 подходящих Resource.

Для каждого показать:

```text
title
URL
type
language
estimated study time
difficulty
short reason for recommendation
```

Например:

```text
1. Article — 12 min
   ...
   Почему подходит: ...

2. Video — 15 min
   ...
   Почему подходит: ...

3. Documentation — 18 min
   ...
   Почему подходит: ...
```

Не выбирать Resource молча.

Пользователь делает выбор.

---

# 12. Resource Is Not Unit Definition

Выбранный Resource не должен становиться смыслом Unit.

Основной принцип:

```text
Unit = what we learn
Resource = how we learn it this time
```

Если пользователь говорит:

```text
этот материал не подходит
```

Codex должен иметь возможность предложить другой Resource без изменения Unit goal.

---

# 13. Study Focus

Перед тем как пользователь уйдёт читать/смотреть Resource, Codex должен показать 2–3 конкретных вопроса.

Например:

```text
Во время материала обрати внимание:

1. Как автор отделяет functional requirements от non-functional?
2. Какие constraints влияют на архитектуру сильнее всего?
3. В какой момент стоит ограничить scope задачи?
```

Не показывать ответы заранее.

---

# 14. Study Step

После Study Focus пользователь изучает выбранный Resource.

Codex не должен считать Unit пройденной после сообщения:

```text
прочитал
посмотрел
готово
```

После этого обязательно начинается проверка.

---

# 15. Active Recall

Первый этап проверки должен происходить без опоры на материал.

Codex задаёт короткие вопросы, проверяющие:

```text
recall
understanding
```

Количество вопросов должно быть небольшим.

Цель — проверить способность восстановить основные идеи своими словами.

---

# 16. Practice

После Recall дать небольшую практическую задачу или scenario.

Она должна проверять:

```text
application
```

Для System Design предпочтительнее scenario, требующий принять решение или объяснить trade-off, а не factual quiz.

---

# 17. User Takeaways

Перед завершением попытки попросить пользователя сформулировать примерно 2–4 ключевые мысли своими словами.

Например:

```text
Сформулируй коротко, что ты вынес из этой Unit.
```

Codex может указать на существенную ошибку.

Codex не должен самостоятельно писать Takeaways вместо пользователя.

---

# 18. Evidence

После проверки создать immutable Primary Event:

```text
evidence/<unit-id>/<evidence-id>.yaml
```

Минимально:

```yaml
id: ...

unit: define-problem-and-requirements
session: 2026-09-14-001

type: initial

created_at: ...

resource:
  title: ...
  url: ...
  type: article

recall:
  prompts:
    - ...
  answers:
    - ...

practice:
  prompt: ...
  answer: ...

takeaways:
  - ...
  - ...

observations:
  - ...
```

Evidence не содержит итоговый mastery.

После создания Evidence не изменяется.

---

# 19. Evidence Validation

Добавить schema + validation.

Проверять:

```text
known Unit
known Session
unique Evidence ID
attempt type
prompt/answer presence
takeaways
```

Не перезаписывать существующий Evidence с тем же ID.

---

# 20. Assessment

После записи Evidence Codex анализирует его и создаёт отдельный Assessment Event.

Путь:

```text
assessments/<evidence-id>/001.yaml
```

Пример:

```yaml
id: ...

evidence: ...

type: initial

created_at: ...

result:
  recall: good
  understanding: good
  application: hard

gaps:
  - >
    Хорошо определяет requirements,
    но недостаточно явно фиксирует constraints.

summary: >
  ...
```

Допустимые оценки для Stage 2 должны быть заранее ограничены schema.

Например:

```text
failed
hard
good
easy
```

или другой небольшой фиксированный enum.

Не использовать произвольные numerical scores без необходимости.

---

# 21. Assessment Boundary

Важно:

```text
Evidence = фактический ответ пользователя
Assessment = интерпретация ответа Codex
```

Assessment нельзя записывать внутрь Evidence.

На Stage 2 reevaluation ещё не реализуется.

---

# 22. Progress

После Evidence + Assessment deterministic script обновляет:

```text
progress/units.yaml
```

Например:

```yaml
define-problem-and-requirements:

  status: verified

  attempts: 1

  mastery:
    recall: good
    understanding: good
    application: hard

  latest_evidence: ...
  latest_assessment: ...

  last_attempt: ...
```

Progress является Derived Data.

Codex не должен вручную определять формат или напрямую редактировать его произвольным образом.

---

# 23. Progress Rules

Для Stage 2 достаточно простой deterministic mapping.

Например:

```text
существенный failed
    → learning/practice

достаточный recall + understanding + application
    → verified

application weak
    → practice
```

Не добавлять пока:

```text
next_review
interval_days
review schedule
```

Это следующий Stage.

---

# 24. Frontier After Completion

После завершения Unit система должна не предлагать её как новую Unit в следующей Session.

Допускается минимальное обновление Frontier либо фильтрация через Progress.

Не нужно пока строить сложный adaptive frontier.

Главное:

```text
completed/verified Unit
не должна выглядеть как untouched Skeleton
```

---

# 25. Complete Session

После успешной записи:

```text
Evidence
Assessment
Progress
```

Session переводится в:

```yaml
status: completed

actual:
  unit: define-problem-and-requirements

evidence:
  - <evidence-id>

completed_at: ...
```

Session должна ссылаться на Evidence, а не дублировать содержимое ответа пользователя.

---

# 26. Updated Status

После Session команда:

```text
status
```

должна показывать уже реальное состояние.

Например:

```text
System Design

Completed attempts: 1

Verified:
- Define problem and requirements

Needs practice:
- application: requirements/constraints

Primary focus:
Design process

Next:
1. Estimate workload — 20 min
2. Trace request lifecycle — 25 min
...
```

Status должен читать repository files.

Он не должен зависеть от памяти разговора.

---

# 27. Skills

На Stage 2 добавить минимум:

```text
run-session
initialize-unit
find-resources
run-study
assess-answer
```

Допускается объединить некоторые из них.

Главное — разделение ответственности, а не количество файлов.

---

# 28. Deterministic Scripts

Добавить операции примерно следующего уровня:

```text
create-session
validate-session

validate-unit

create-evidence
validate-evidence

create-assessment
validate-assessment

update-progress

complete-session

read-status
```

Codex предоставляет semantic content.

Scripts отвечают за безопасную запись состояния.

---

# 29. Schemas

Добавить schemas:

```text
unit
session
evidence
assessment
progress
```

Не проектировать поля Reviews заранее.

---

# 30. Failure Safety

Особенно важно соблюдать порядок записи.

Предпочтительный поток:

```text
create Session
       ↓
create/update Unit
       ↓
learning interaction
       ↓
write Evidence
       ↓
write Assessment
       ↓
update Progress
       ↓
complete Session
```

Если Progress update не удался:

```text
Evidence и Assessment не удалять.
```

Primary Data важнее Derived State.

---

# 31. Tests

Минимальные deterministic tests:

```text
Unit references unknown Node
invalid Unit state/data
Evidence references unknown Unit
Evidence references unknown Session
duplicate Evidence ID
Assessment references unknown Evidence
invalid assessment enum
Progress updates from valid Assessment
completed Unit does not appear as untouched next Unit
Session completion references existing Evidence
```

Stage 1 tests должны продолжать проходить.

---

# 32. Semantic Acceptance Test

Использовать уже созданный:

```text
System Design
```

repository.

Пользователь запускает:

```text
У меня есть 25 минут
```

Система должна:

1. прочитать существующий Frontier;
2. предложить разумную Unit;
3. материализовать её;
4. предложить 2–3 Resource;
5. дать Study Focus;
6. дождаться изучения;
7. провести Recall;
8. провести Practice;
9. запросить Takeaways;
10. сохранить Evidence;
11. сохранить Assessment;
12. обновить Progress;
13. закрыть Session;
14. показать обновлённый Status.

---

# 33. Persistence Test

После завершения Session:

1. полностью закрыть Codex;
2. открыть repository в новом контексте;
3. написать:

```text
status
```

Новый Codex должен понять:

```text
что было изучено
каков Assessment
где есть gaps
какие Unit доступны следующими
```

исключительно из файлов repository.

---

# 34. Definition of Done

Stage 2 завершён, если можно реально провести первую учебную Session по System Design и после неё repository содержит согласованную цепочку:

```text
Session
   ↓
Unit
   ↓
Evidence
   ↓
Assessment
   ↓
Progress
```

и новый Codex context способен продолжить работу с этого состояния.

После этого не реализовывать Reviews автоматически.

Сначала провести несколько настоящих Sessions и оценить:

```text
удобство выбора Unit
качество Resource recommendations
полезность Study Focus
качество Recall
качество Practice
адекватность Assessment
полезность Status
```

Только после практической проверки переходить к Stage 3.
