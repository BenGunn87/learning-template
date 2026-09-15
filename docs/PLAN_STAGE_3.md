# Stage 3 — Targeted Practice + Reviews

## 1. Цель

Замкнуть основной цикл обучения после Stage 2.

После Stage 3 система должна уметь:

```text
изучить Unit
   ↓
получить Assessment
   ↓
определить слабый компонент
   ↓
дать целевую Practice
   ↓
Verified
   ↓
назначить Review
   ↓
через несколько дней проверить снова
   ↓
адаптировать следующий интервал
```

Ключевое изменение:

> Unit со статусом `practice` не должна автоматически проходить полный Study Flow заново.

---

# 2. Scope

Реализовать:

* targeted practice;
* повторную попытку Unit без повторного изучения материала;
* review scheduling;
* due reviews;
* review budget;
* review session flow;
* новое Evidence для каждой попытки;
* новое Assessment;
* обновление mastery;
* простой spaced repetition algorithm;
* отображение reviews в `status`.

---

# 3. Не входит в Stage 3

Пока не реализовывать:

* Pause / Resume;
* Recalibration после долгого перерыва;
* Graph evolution;
* автоматический missing-prerequisite workflow;
* Assessment reevaluation;
* сложный FSRS;
* Web UI;
* Learning Core upgrade.

---

# 4. Новая логика выбора действия

При старте:

```text
session 25
```

система должна учитывать:

```text
1. Units со status=practice
2. Due Reviews
3. Untouched Frontier Units
```

Но это не означает жёсткий приоритет одного над другим.

Session planner должен собрать разумный план с учётом бюджета времени.

---

# 5. Targeted Practice

Если Progress показывает:

```yaml
status: practice

mastery:
  recall: good
  understanding: good
  application: hard
```

система не должна снова запускать:

```text
Resource
→ Study Focus
→ Study
```

Вместо этого:

```text
read previous Evidence
      ↓
identify weak dimension
      ↓
generate new scenario
      ↓
user solves it
      ↓
new Evidence
      ↓
new Assessment
```

---

# 6. Practice Principle

Practice должна быть направлена именно на gap.

Например:

```text
application = hard
```

→ новый scenario / decision / trade-off.

```text
recall = hard
```

→ active recall без материала.

```text
understanding = hard
```

→ объяснение причин, механизмов, сравнений и edge cases.

---

# 7. No Question Memorization

Новая попытка не должна повторять предыдущий prompt дословно.

Codex должен читать последние Evidence и создавать новую проверку той же способности.

Принцип:

> Проверяем знание, а не память конкретного вопроса.

---

# 8. Practice Evidence

Каждая Practice создаёт новый Evidence:

```text
evidence/<unit-id>/
    initial.yaml
    practice-001.yaml
    practice-002.yaml
```

Например:

```yaml
id: ...

unit: frame-a-system-design-problem
session: ...

type: practice

target:
  dimension: application

based_on:
  evidence: <previous-evidence-id>

practice:
  prompt: ...
  answer: ...

takeaways:
  - ...
```

Старый Evidence не изменяется.

---

# 9. Practice Assessment

Для новой попытки создаётся обычный новый Assessment.

Например:

```yaml
result:
  recall: good
  understanding: good
  application: good
```

Progress строится по последнему актуальному состоянию Unit.

---

# 10. Transition to Verified

Для MVP использовать простое правило.

Например:

```text
recall != failed
AND
understanding != failed
AND
application in {good, easy}
        ↓
verified
```

Если остаётся:

```text
application = hard
```

Unit остаётся:

```text
practice
```

Если:

```text
recall = failed
OR
understanding = failed
```

Unit возвращается:

```text
learning
```

---

# 11. Verified Starts Review Cycle

Когда Unit впервые становится:

```text
verified
```

deterministic script создаёт review state.

Например:

```yaml
review:
  due: 2026-09-18
  interval_days: 3
  repetitions: 0
```

Это Derived Data внутри Progress.

Отдельная Primary сущность `Review` не требуется.

---

# 12. Review Scheduling

Для MVP использовать простой deterministic algorithm.

Результаты:

```text
failed
hard
good
easy
```

Пример начальных интервалов:

```text
failed → 1 day
hard   → 3 days
good   → 7 days
easy   → 14 days
```

Для последующих Review interval изменяется относительно предыдущего.

Можно использовать простой multiplier:

```text
failed → reset to 1
hard   → ×1.5
good   → ×2
easy   → ×3
```

Точные значения должны находиться в config и легко меняться.

---

# 13. Review Config

Добавить в:

```text
config/settings.yaml
```

примерно:

```yaml
review:
  max_session_share: 0.25

  initial_intervals:
    failed: 1
    hard: 3
    good: 7
    easy: 14

  multipliers:
    hard: 1.5
    good: 2.0
    easy: 3.0
```

Не зашивать значения глубоко в код.

---

# 14. Due Review

Unit считается due, если:

```text
review.due <= current date
```

Scripts должны уметь детерминированно получить:

```text
get due reviews
```

Codex не вычисляет даты самостоятельно.

---

# 15. Review Budget

Review не должны захватывать всю Session.

По умолчанию:

```text
max 25% Session budget
```

Например:

```text
session 25
```

может дать:

```text
~5 min Review
+
~20 min new learning / practice
```

Это ориентир, а не таймер.

Если due Reviews много, часть переносится на будущие Sessions.

Overdue Reviews не являются долгом.

---

# 16. Review Selection

Если due Units больше, чем помещается в budget, scripts формируют candidates.

Codex может приоритизировать по:

* степени просрочки;
* слабым mastery dimensions;
* importance Nodes;
* связи с текущим Primary Focus.

Но система не должна пытаться пройти весь backlog.

---

# 17. Review Flow

Для выбранной Unit:

```text
read Unit
   ↓
read recent Evidence
   ↓
read gaps
   ↓
generate new recall/scenario
   ↓
user answer
   ↓
Evidence(type=review)
   ↓
Assessment
   ↓
Review Outcome
   ↓
new interval
```

Resource обычно не нужен.

---

# 18. Review Should Be Adaptive

Если прошлый gap был:

```text
application
```

Review должен преимущественно проверять применение.

Если Unit долго держится хорошо, Review может становиться более интеграционным.

---

# 19. Review Evidence

Создаётся обычный Primary Evidence:

```yaml
type: review

unit: ...
session: ...

based_on:
  previous_evidence: ...

prompt: ...
answer: ...

takeaways:
  - ...
```

Review не является отдельной исторической сущностью.

---

# 20. Review Assessment

Assessment остаётся тем же типом сущности.

Например:

```yaml
result:
  recall: good
  understanding: good
  application: good

review_outcome: good
```

`review_outcome` может вычисляться script на основании Assessment либо сохраняться отдельным deterministic result.

Предпочтительно не заставлять Codex самостоятельно назначать interval.

---

# 21. Review → Progress

После Assessment script обновляет:

```yaml
status: verified

mastery:
  recall: good
  understanding: good
  application: good

review:
  last: 2026-09-18
  due: 2026-10-02
  interval_days: 14
  repetitions: 2
```

---

# 22. Failed Review

Если Review показывает существенную потерю знания:

```text
recall failed
OR understanding failed
```

Unit может вернуться:

```text
learning
```

Если теория сохраняется, но application просела:

```text
practice
```

При этом история review сохраняется.

---

# 23. Session Planning

Теперь `run-session` должен различать минимум три типа учебного действия:

```text
study
practice
review
```

Например:

```yaml
plan:
  actions:
    - type: review
      unit: cache-invalidation

    - type: practice
      unit: frame-a-system-design-problem
```

или:

```yaml
plan:
  actions:
    - type: review
      unit: quorum-reads-writes

    - type: study
      unit: estimate-workload
```

---

# 24. Session Plan Is Adaptive

Если Practice неожиданно занимает весь доступный бюджет, новую Unit можно не начинать.

Это не является ошибкой Session.

---

# 25. Status

После Stage 3 `status` должен показывать:

```text
Verified
Practice
Learning
Reviews due
```

Например:

```text
System Design

Primary focus:
Design process

Practice:
- Frame a system design problem
  weakness: application

Reviews due:
- none

Verified:
- ...

Next new units:
1. Estimate workload
2. Trace request lifecycle
```

---

# 26. Skills

Добавить или обновить:

```text
run-session
run-practice
run-review
assess-answer
status
```

`run-session` должен выбирать правильный flow:

```text
status=practice
    → run-practice

due review
    → run-review

new Skeleton
    → initialize-unit + run-study
```

---

# 27. Deterministic Scripts

Добавить минимум:

```text
get-practice-units
get-due-reviews

calculate-review-outcome
calculate-next-review

update-progress

plan-session-candidates
```

Codex не должен вычислять Review dates вручную.

---

# 28. Schemas

Обновить схемы:

```text
progress
session
evidence
assessment
settings
```

Evidence `type` должен поддерживать:

```text
initial
practice
review
```

---

# 29. Tests — Practice

Добавить минимум:

```text
practice Unit is preferred over repeating study flow

application=hard
→ status=practice

practice result good
→ verified

failed recall during practice
→ learning

new Practice Evidence does not modify old Evidence
```

---

# 30. Tests — Review

Добавить минимум:

```text
verified Unit gets initial review due date

due Review is detected

not-due Review is not selected

failed Review resets interval

hard Review increases interval modestly

good Review increases interval

easy Review increases interval more

Review Evidence remains append-only

Progress receives new due date
```

---

# 31. Real Acceptance Test — Practice

Использовать текущий реальный результат:

```text
Frame a system design problem
status = practice
application = hard
```

Запустить новую Session.

Ожидаемое поведение:

```text
не предлагать снова читать Resource

дать новый System Design scenario

проверить самостоятельный вывод trade-off

создать новое Evidence

создать новое Assessment
```

Если результат:

```text
application = good
```

Unit должна перейти в:

```text
verified
```

и получить первую Review date.

---

# 32. Real Acceptance Test — Review

Чтобы не ждать несколько дней, в тестовой ветке допустимо вручную/fixture-ом сделать Review due.

После:

```text
session 25
```

система должна:

1. обнаружить due Review;
2. включить её в ограниченный Review budget;
3. дать новый prompt;
4. создать новое Evidence;
5. создать Assessment;
6. пересчитать interval;
7. продолжить Session, если осталось время.

---

# 33. Persistence Test

После Practice или Review:

```text
закрыть Codex
↓
открыть новый context
↓
status
```

Система должна восстановить:

```text
что было practiced
что verified
какие Units находятся в review cycle
когда следующий review
какой gap остаётся
```

только из repository files.

---

# 34. Definition of Done

Stage 3 считается завершённым, если текущая реальная Unit:

```text
Frame a system design problem
```

может пройти путь:

```text
practice
   ↓
new application scenario
   ↓
new Evidence
   ↓
new Assessment
   ↓
verified
   ↓
scheduled Review
   ↓
Review
   ↓
new interval
```

без повторного прохождения первоначального Study Flow.

---

# 35. Главная гипотеза Stage 3

Мы проверяем уже не только способность системы проводить обучение, но и способность **адаптироваться к конкретному пробелу пользователя**.

Критерий качества:

> Если пользователь знает теорию, но плохо применяет её, система должна давать практику, а не ещё одну статью.
