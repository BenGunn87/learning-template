# Stage 4 — Pause, Resume & Multi-session Units

## 1. Цель

Сделать учебную систему устойчивой к реальному режиму коротких и прерывающихся сессий.

После Stage 4 пользователь должен иметь возможность:

```text
начать Unit
   ↓
остановиться в любой момент
   ↓
закрыть Codex
   ↓
вернуться позже
   ↓
продолжить с правильного места
```

Также Session planner должен получить право начинать Unit, даже если она не помещается целиком в оставшееся время.

---

# 2. Основные сценарии

Реализовать:

```text
Pause Session
Resume Session
Continue active Unit
Checkpoint
Multi-session Unit
Recovery after unexpected interruption
Use remaining session time for partial Unit
```

---

# 3. Не входит в Stage 4

Не реализовывать:

```text
Recalibration after long inactivity
Graph evolution
Automatic missing-prerequisite routing
Assessment reevaluation
Advanced rebuild/repair
Web UI
Multi-agent architecture
```

---

# 4. Главное архитектурное правило

`paused` относится только к Session.

Unit не получает статус:

```text
paused
```

Unit продолжает иметь учебный статус:

```text
learning
practice
verified
```

Session хранит информацию о том, где пользователь остановился.

---

# 5. Session States

Session должна поддерживать:

```text
active
paused
completed
```

Дополнительно может существовать техническое состояние:

```text
abandoned
```

только если оно действительно понадобится.

Для MVP достаточно:

```text
active
paused
completed
```

---

# 6. Checkpoint

При паузе Session сохраняет checkpoint.

Пример:

```yaml
checkpoint:
  unit: estimate-workload
  action: study
  stage: study

  completed_steps:
    resource_selected: true
    study_focus_shown: true
    study_completed: false
    recall_completed: false
    practice_completed: false

  resource:
    title: ...
    url: ...

  note: >
    Пользователь остановился после первой части материала.
```

Checkpoint — Primary Data внутри Session.

---

# 7. Checkpoint Principle

Checkpoint должен отвечать:

> Что уже произошло и с какого места безопасно продолжить?

Он не должен пытаться сохранять весь разговор.

Не хранить полный transcript Codex.

---

# 8. Pause UX

Пользователь может написать естественно:

```text
пауза
остановимся здесь
продолжу позже
мне нужно отвлечься
```

Codex должен:

1. определить текущую Session;
2. определить текущую Unit/action;
3. сохранить checkpoint;
4. перевести Session в `paused`;
5. не создавать Assessment, если проверка не была завершена;
6. не ухудшать Progress.

---

# 9. Pause Does Not Create Failure

Пауза никогда не означает:

```text
failed
hard
practice
```

сама по себе.

Если пользователь просто не успел закончить Unit, mastery не меняется.

---

# 10. Resume UX

При следующем:

```text
session 20
```

или:

```text
давай продолжим
```

система сначала проверяет:

```text
active/paused Sessions
```

Если существует paused Session, Codex должен сообщить:

```text
Есть незавершённая Session.

Unit:
Estimate workload

Этап:
Study

Продолжить?
```

По умолчанию предпочтительно продолжение.

---

# 11. Resume Same Session vs New Session

Для MVP выбрать простую модель:

> Resume продолжает ту же логическую Session.

То есть:

```text
Session created
→ active
→ paused
→ active
→ completed
```

Один Session ID сохраняется.

---

# 12. Time Segments

Чтобы реальная длительность Session не терялась, добавить segments.

Пример:

```yaml
segments:
  - started_at: ...
    ended_at: ...

  - started_at: ...
    ended_at: ...
```

Это позволит отличать:

```text
Session существовала 3 дня
```

от:

```text
пользователь реально учился 32 минуты
```

---

# 13. Active Time

Scripts должны уметь вычислять:

```text
active_minutes
```

как сумму завершённых segments.

Не использовать:

```text
completed_at - started_at
```

как реальное учебное время.

Это особенно важно после нашего первого теста, где пользователь отвлекался.

---

# 14. Session Time Budget

`time_budget_minutes` относится к конкретному заходу пользователя, а не обязательно ко всей жизни Session.

Поэтому при Resume:

```text
session 15
```

система получает новый доступный budget:

```text
15 min
```

но продолжает существующую Session.

Можно хранить:

```yaml
segments:
  - budget_minutes: 25
  - budget_minutes: 15
```

---

# 15. Multi-session Unit

Unit может жить через несколько временных заходов.

Пример:

```text
Session segment A:
  Study 12 min
  → pause

Session segment B:
  Finish Study
  Recall
  → pause

Session segment C:
  Practice
  Evidence
  Assessment
  → completed
```

При этом Unit остаётся одной и той же.

---

# 16. Partial Unit Planning

После Stage 4 planner больше не должен требовать, чтобы новая Unit целиком помещалась в remaining budget.

Например:

```text
Session: 25 min

Review: 5 min
Remaining: 20 min

Next Unit estimate: 25 min
```

Теперь допустимо:

```text
Review 5 min
+
Start Unit 20 min
+
Checkpoint
```

---

# 17. Planning Rule

Если Unit не помещается целиком, planner может начать её, если:

* это разумное следующее действие;
* remaining budget достаточен для meaningful progress;
* Unit поддерживает checkpoint;
* пользователь не запретил начинать незавершаемую Unit.

---

# 18. Minimum Useful Slice

Чтобы не начинать 25-минутную Unit при оставшейся 1 минуте, добавить configurable threshold.

Например:

```yaml
session:
  min_partial_unit_minutes: 10
```

Если осталось меньше:

```text
не начинать новую Unit
```

Если осталось ≥ threshold:

```text
можно начать Unit частично
```

---

# 19. Resume Flow by Stage

Checkpoint должен позволять продолжать без повторения уже выполненных этапов.

Например:

```text
checkpoint.stage = study
```

→ не предлагать Resource заново, если он уже выбран.

```text
checkpoint.stage = recall
```

→ не возвращать пользователя к статье.

```text
checkpoint.stage = practice
```

→ продолжить Practice.

---

# 20. Resource Persistence

Если Resource уже выбран:

```yaml
checkpoint:
  resource:
    ...
```

Resume должен использовать его.

Не проводить повторный resource selection без причины.

---

# 21. Study Focus Persistence

Если Study Focus уже был показан:

```yaml
study_focus_shown: true
```

его можно кратко напомнить, но не считать новым этапом.

---

# 22. Evidence Boundary

Evidence создаётся только тогда, когда существует содержательная завершённая попытка проверки.

Пауза во время:

```text
study
```

не создаёт Evidence.

Пауза во время незавершённого Practice тоже не должна создавать ложное Evidence.

---

# 23. Partial Answers

Если пользователь уже дал содержательный ответ, но проверка ещё не завершена, можно сохранить его внутри checkpoint.

Например:

```yaml
checkpoint:
  partial_interaction:
    practice_answer: >
      ...
```

Это ещё не Evidence.

После завершения проверки информация переносится в новый Evidence.

---

# 24. Unexpected Interruption

Если Codex/terminal закрыт без команды pause:

```text
Session остаётся active
```

Следующий запуск должен обнаружить stale active Session.

---

# 25. Stale Active Session

При следующем:

```text
status
```

или:

```text
session 20
```

система должна показать:

```text
Обнаружена незавершённая Session.

Started:
...

Unit:
...

Последний checkpoint:
...
```

и предложить восстановление.

---

# 26. Recovery

Если checkpoint существует:

```text
resume from checkpoint
```

Если Session active, но checkpoint не успел сохраниться:

* не придумывать состояние;
* использовать последние надёжно записанные данные;
* спросить пользователя, где он остановился, если необходимо.

---

# 27. Idempotency

Повторный Resume не должен:

* создавать новую Session;
* дублировать segments;
* повторно создавать Evidence;
* повторно завершать action.

---

# 28. Session Actions

Session actions должны поддерживать состояние выполнения.

Например:

```yaml
plan:
  actions:
    - type: review
      unit: ...

    - type: study
      unit: estimate-workload

actual:
  actions:
    - type: review
      unit: ...
      status: completed

    - type: study
      unit: estimate-workload
      status: in_progress
```

После Resume:

```yaml
status: completed
```

---

# 29. Action States

Минимально:

```text
planned
in_progress
completed
```

Не обязательно делать отдельную сложную state machine.

---

# 30. Complete Session

Session становится:

```text
completed
```

когда:

* пользователь явно завершил Session;
* или все запланированные actions закончены;
* или пользователь решил закончить текущий заход без активного незавершённого action.

---

# 31. Paused Session

Session становится:

```text
paused
```

если существует незавершённое действие, которое предполагается продолжить позже.

---

# 32. Status

`status` должен показывать paused/active work.

Например:

```text
Paused Session:

Estimate workload
Stage: study
Resource selected
Study Focus completed

Next action:
Continue Unit
```

---

# 33. Frontier Interaction

Unit, которая уже начата, должна иметь приоритет перед новой untouched Unit.

Planner не должен создавать второй экземпляр той же Unit.

---

# 34. Progress Interaction

Начатая, но незавершённая Unit может иметь:

```text
status: learning
```

Но Progress не должен делать вывод о mastery только потому, что Session поставлена на pause.

---

# 35. Practice Resume

Если `status=practice` и targeted practice была прервана:

```text
resume same practice
```

а не генерировать новый scenario автоматически.

---

# 36. Review Resume

Если Review начат и прерван:

```text
resume same review
```

Review due date не должна пересчитываться до завершённой Assessment.

---

# 37. Schemas

Обновить:

```text
session.schema.yaml
```

для поддержки:

```text
paused
checkpoint
segments
action status
```

При необходимости обновить Unit/Progress schemas минимально.

---

# 38. Deterministic Scripts

Добавить примерно:

```text
pause-session
resume-session
detect-resumable-session
start-session-segment
close-session-segment
calculate-active-minutes
update-checkpoint
```

---

# 39. Skills

Обновить:

```text
run-session
run-study
run-practice
run-review
status
```

Добавить при необходимости:

```text
pause-session
resume-session
```

Но количество Skills вторично.

---

# 40. Tests — Pause

Минимум:

```text
active Session → pause
checkpoint saved
pause does not create Evidence
pause does not change mastery
pause is idempotent
```

---

# 41. Tests — Resume

```text
paused Session detected
resume keeps same Session ID
new segment created
checkpoint preserved
already completed steps are not repeated
```

---

# 42. Tests — Multi-session Unit

```text
Unit starts in segment 1
Session pauses
Unit resumes in segment 2
Evidence created only once after completion
Progress updated only after Assessment
```

---

# 43. Tests — Unexpected Interruption

```text
stale active Session detected
system does not create duplicate Session
recovery uses last checkpoint
```

---

# 44. Tests — Remaining Budget

Сценарий:

```text
25 min Session
5 min Review
20 min remaining
25 min Unit
```

После Stage 4 ожидается:

```text
Review
+
partial Study
+
checkpoint
```

а не:

```text
Review only
```

при условии:

```text
remaining >= min_partial_unit_minutes
```

---

# 45. Real Acceptance Test A — Manual Pause

Использовать текущий System Design repository.

Запустить:

```text
У меня есть 15 минут.
```

Начать новую Unit.

Во время Study написать:

```text
Остановимся здесь.
```

Проверить:

```text
Session status = paused
checkpoint exists
Evidence not created
Progress mastery unchanged
```

---

# 46. Real Acceptance Test B — New Context Resume

Полностью закрыть Codex.

Открыть repository заново.

Написать:

```text
У меня есть 20 минут.
```

Ожидаем:

```text
обнаружена paused Session
→ предложено продолжение
→ Resource не выбирается заново
→ Unit продолжается с checkpoint
```

---

# 47. Real Acceptance Test C — Interrupt Practice

В Unit со статусом:

```text
practice
```

начать новый scenario.

Ответить частично.

Поставить pause.

После Resume система должна продолжить тот же Practice, а не создавать новый.

---

# 48. Real Acceptance Test D — Review + Partial Unit

Создать due Review.

Запустить:

```text
session 25
```

Ожидается:

```text
~5 min Review
+
start next 25-min Unit with remaining ~20 min
+
checkpoint if Unit not completed
```

Это главный новый planner behavior Stage 4.

---

# 49. Persistence Test

После Pause:

```text
закрыть Codex
↓
новый context
↓
status
```

Новый Codex должен восстановить:

```text
какая Session paused
какая Unit активна
какой stage
что уже выполнено
какой Resource выбран
что делать дальше
```

только из repository.

---

# 50. Definition of Done

Stage 4 завершён, если реальная Unit может пройти:

```text
start
  ↓
partial study
  ↓
pause
  ↓
close Codex
  ↓
new context
  ↓
resume
  ↓
practice
  ↓
pause
  ↓
resume
  ↓
Evidence
  ↓
Assessment
  ↓
Progress
  ↓
completed Session
```

без дублирования Unit, Evidence или Session.

---

# 51. Главная гипотеза Stage 4

Система должна соответствовать реальной жизни пользователя:

> У меня не всегда есть идеальные непрерывные 25 минут, но любое небольшое окно времени должно позволять безопасно продолжить обучение без потери контекста.
