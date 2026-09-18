Нужно исправить hardening-проблемы в Stage 5, связанные с тем, как Assessment превращается в Gap signals.

Не переделывай Stage 5 целиком. Сохрани текущую архитектуру `Gap`, `Interest`, adaptive frontier и routing reasons. Изменения должны быть минимальными и сосредоточенными на **точной атрибуции Assessment → Gap**.

# Проблемы

Сейчас gap detection использует все значения `Assessment.result` и общий список `observed_nodes`.

Это создаёт три проблемы.

## 1. Carried-forward dimensions создают ложные gap signals

В targeted Practice может реально проверяться только одна dimension, например:

```text
application
```

При этом `recall` и `understanding` могут быть перенесены из предыдущего Assessment для Progress.

Пример:

```text
Evidence 1:
recall: hard

→ gap recall = detected

Evidence 2:
targeted practice проверяет только application

Assessment result:
recall: hard          # carried forward, НЕ tested now
understanding: good   # carried forward
application: good     # actually evaluated
```

Текущий gap detection может воспринять второй `recall: hard` как новый независимый signal и перевести gap:

```text
detected → confirmed
```

хотя recall второй раз вообще не проверялся.

Это нужно исключить.

---

## 2. `observed_nodes` слишком грубый

Сейчас Assessment может содержать общий список:

```yaml
observed_nodes:
  - document-databases
  - graph-databases
```

и одновременно разные dimensions.

Но реально может быть так:

```text
recall       → проверял document-databases
application  → проверял graph-databases
```

Нельзя делать декартово произведение:

```text
all nodes × all weak dimensions
```

Gap должен создаваться только на node, который реально проверялся конкретной dimension.

---

## 3. `detected → resolved`

Сейчас lifecycle поддерживает:

```text
detected → confirmed → resolved
```

но не нормально обрабатывает распространённый сценарий:

```text
Evidence 1:
application: hard
→ gap = detected

Targeted practice:
application: good
→ ?
```

Если слабость была успешно устранена до второго weak signal, gap не должен вечно оставаться `detected`.

Нужно разрешить:

```text
detected → resolved
```

если новая Evidence специально перепроверила эту же dimension + node и дала:

```text
good
easy
```

Это означает:

> слабость была замечена, но устранена до того, как стала устойчивым confirmed gap.

История gap при этом сохраняется.

---

# Основное изменение модели Assessment

Добавь явную информацию о том, **что именно было реально оценено в текущей Evidence**.

Предпочтительная модель:

```yaml
evaluated:
  recall:
    nodes:
      - document-databases

  application:
    nodes:
      - graph-databases
```

Если dimension не проверялась в этой Evidence, её НЕ должно быть в `evaluated`.

При этом `result` может по-прежнему содержать полное mastery state:

```yaml
result:
  recall: hard
  understanding: good
  application: good
```

Это допустимо для Progress.

Ключевой принцип:

```text
result
→ current mastery state / progress input

evaluated
→ what this Evidence actually tested
→ only this may create/update Gap signals
```

Не используй carried-forward dimension как новый gap signal.

---

# Assessment schema

Обнови Assessment schema.

Пример:

```yaml
evaluated:
  type: object
  properties:
    recall:
      type: object
      properties:
        nodes:
          type: array
          items:
            type: string

    understanding:
      type: object
      properties:
        nodes:
          type: array
          items:
            type: string

    application:
      type: object
      properties:
        nodes:
          type: array
          items:
            type: string
```

Точный YAML адаптируй к текущему стилю schemas.

Не обязательно требовать все три dimensions.

Например targeted practice может иметь только:

```yaml
evaluated:
  application:
    nodes:
      - data-model-selection
```

---

# Gap detection

Измени gap detection так, чтобы он обходил только:

```text
Assessment.evaluated
```

Алгоритм концептуально:

```text
for each evaluated dimension:
    result = assessment.result[dimension]

    for each node in evaluated[dimension].nodes:
        process signal(node, dimension, result)
```

Не использовать:

```text
all observed_nodes × all result dimensions
```

как источник signals.

`observed_nodes`, если он нужен другим частям системы, можно оставить для compatibility, но Gap logic не должна на него полагаться как на точную attribution-модель.

---

# Weak signal

Weak signal остаётся:

```text
hard
failed
```

Но signal создаётся только если:

```text
dimension exists in evaluated
AND
node exists in evaluated[dimension].nodes
```

---

# Successful signal / resolving

Для:

```text
good
easy
```

по реально evaluated dimension + node:

### confirmed gap

```text
confirmed → resolved
```

как сейчас.

### detected gap

Также разрешить:

```text
detected → resolved
```

Если эта Evidence действительно проверяет тот же:

```text
node + dimension
```

Не требовать предварительного `confirmed`.

---

# Gap validator/schema

Если текущая schema/validator требует для `resolved` минимум два weak signals, ослабь это правило.

`resolved` должен быть допустим в двух случаях:

```text
hard → good
```

или:

```text
hard → hard → good
```

То есть количество weak signals само по себе не определяет допустимость `resolved`.

История должна позволять:

```yaml
history:
  - status: detected
    at: ...
    evidence: ...

  - status: resolved
    at: ...
    evidence: ...
```

---

# Reopen behavior

Сохрани существующее правило:

```text
resolved + new hard/failed
→ confirmed
```

с тем же Gap ID.

Новый gap не создаётся.

Это применимо независимо от того, был gap когда-то confirmed раньше или был закрыт прямо из detected.

---

# Skills

Обнови assessment-related skills.

Особенно проверь:

```text
.agents/skills/assess-answer/SKILL.md
```

и любые skills для:

```text
study
practice
review
assessment
```

Codex при создании Assessment должен явно определить:

```text
which dimensions were actually evaluated
which graph nodes each evaluated dimension tested
```

Пример targeted practice:

```yaml
result:
  recall: hard
  understanding: good
  application: good

evaluated:
  application:
    nodes:
      - data-model-selection
```

Здесь `recall: hard` НЕ создаёт новый recall signal.

---

# Initial study example

Если Initial Evidence действительно проверяет все три dimensions:

```yaml
evaluated:
  recall:
    nodes:
      - quorum

  understanding:
    nodes:
      - quorum

  application:
    nodes:
      - quorum
```

Это нормально.

---

# Multi-node example

Если одна Evidence проверяет разные знания:

```yaml
result:
  recall: hard
  application: hard

evaluated:
  recall:
    nodes:
      - document-databases

  application:
    nodes:
      - graph-databases
```

Ожидаемо:

```text
recall gap only on document-databases

application gap only on graph-databases
```

Не создавать:

```text
application gap on document-databases
recall gap on graph-databases
```

---

# Backward compatibility

Мы всё ещё на стадии тестирования, поэтому migration framework не нужен.

Но существующие Assessment-файлы предыдущих Stage могут не иметь `evaluated`.

Выбери безопасное поведение.

Предпочтительно:

```text
old Assessment without evaluated
→ valid historical data
→ do not infer new gap signals from it automatically
```

Не пытайся угадывать точную attribution старых Assessment.

Если validator должен принимать legacy Assessment без `evaluated`, сделай поле optional для старых данных, но новые Assessment должны его записывать.

Если текущая архитектура имеет лучший простой способ compatibility — используй его, но не вводи migration framework.

---

# Tests

Добавь tests минимум для следующих случаев.

## 1. Carried-forward dimension does not confirm gap

Evidence 1:

```yaml
result:
  recall: hard

evaluated:
  recall:
    nodes: [node-a]
```

→ gap:

```text
node-a + recall = detected
```

Evidence 2:

```yaml
result:
  recall: hard
  application: good

evaluated:
  application:
    nodes: [node-a]
```

Ожидаемо:

```text
recall gap remains detected
```

Он НЕ становится confirmed.

---

## 2. Second real evaluation confirms gap

Evidence 2:

```yaml
result:
  recall: hard

evaluated:
  recall:
    nodes: [node-a]
```

Ожидаемо:

```text
detected → confirmed
```

---

## 3. Dimension-to-node attribution

Assessment:

```yaml
result:
  recall: hard
  application: hard

evaluated:
  recall:
    nodes: [node-a]

  application:
    nodes: [node-b]
```

Ожидаемо:

```text
node-a + recall gap
node-b + application gap
```

И НЕ:

```text
node-a + application
node-b + recall
```

---

## 4. Detected → resolved

First Evidence:

```text
application: hard
```

evaluated on:

```text
node-a
```

→ `detected`.

Second targeted Practice:

```text
application: good
```

evaluated on same `node-a`.

Ожидаемо:

```text
detected → resolved
```

---

## 5. Confirmed → resolved

Сохрани существующий:

```text
hard → hard → good
```

---

## 6. Resolved → confirmed

После:

```text
hard → good
```

ещё один реально evaluated:

```text
hard
```

должен дать:

```text
resolved → confirmed
```

с тем же gap ID.

---

## 7. Legacy Assessment

Assessment без `evaluated`:

* должен оставаться читаемым/валидным, если нужен backward compatibility;
* не должен неожиданно создавать новые Gap signals при rebuild/update.

---

# Regression

Все существующие Stage 1–5 tests должны продолжать проходить.

Особенно не сломать:

```text
targeted practice
review
Progress calculation
pause/resume/recovery
Interest lifecycle
blocking gaps
adaptive frontier
routing reasons
```

---

# Scope constraints

Не добавляй:

* probabilistic mastery;
* assessment re-evaluation framework;
* migration framework;
* новую Gap сущность;
* новую routing architecture;
* сложную inference систему.

Это точечный hardening существующего Stage 5.

Главный новый инвариант:

> Gap signals создаются только из dimensions и graph nodes, которые реально проверялись текущей Evidence.

И второй:

> `Assessment.result` может содержать carried-forward mastery, но carried-forward значения не являются новым Evidence signal.

---

# Verification

После изменений запусти:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/learning.py validate
```

Если реальные команды отличаются — используй актуальные.

В финальном summary укажи:

1. как изменилась Assessment schema;
2. как теперь представляется `evaluated`;
3. как Gap logic отличает tested от carried-forward dimensions;
4. как решена node attribution;
5. как работает `detected → resolved`;
6. какие compatibility decisions приняты для старых Assessment;
7. какие tests добавлены;
8. проходят ли все regression tests.
