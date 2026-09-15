Нужно исправить edge case в Stage 4 recovery.

## Проблема

Сейчас recovery для stale `active` Session корректно работает, если есть сохранённый checkpoint: старый segment закрывается по `checkpoint.updated_at`.

Но если checkpoint отсутствует, `resume-session` предлагает сначала реконструировать checkpoint, а потом вызвать recovery. Это опасно: новый checkpoint получает текущий timestamp, и система может ошибочно посчитать всё время между старым `segment.started_at` и моментом восстановления как active learning time.

Пример:

```text
10:00 Session started
10:03 process crashed
18:00 recovery
```

Если checkpoint создаётся в 18:00 до recovery, система потенциально может записать почти 8 часов active time.

Наш принцип:

> Известное время считаем. Неизвестное время не реконструируем.

## Требуемое поведение

### Recovery с существующим checkpoint

Если stale active Session уже имеет checkpoint:

```text
old segment ends at checkpoint.updated_at
new segment starts at recovered_at
checkpoint semantic state is preserved
```

### Recovery без checkpoint

Если checkpoint отсутствует:

1. recovery без дополнительного semantic state должен отказать и потребовать user input;
2. пользователь сообщает только смысловое состояние:

    * current Unit;
    * current action;
    * current stage;
    * completed steps;
    * selected Resource, если известен;
    * partial interaction, если она есть;
3. пользователь НЕ должен оценивать elapsed time;
4. interrupted segment закрывается консервативно по:

```text
segment.started_at
```

то есть неизвестное active time считается равным нулю;
5. затем открывается новый segment в `recovered_at`;
6. reconstructed checkpoint сохраняется уже как состояние нового segment.

Иными словами:

```text
checkpoint exists
→ close old segment at checkpoint.updated_at

checkpoint missing
→ close old segment at segment.started_at
→ open new segment
→ save reconstructed checkpoint in new segment
```

## Что нужно изменить

Проверь текущую реализацию сам и внеси минимально необходимые изменения, сохраняя существующую архитектуру Stage 4.

Ожидаемо потребуется затронуть:

```text
scripts/learning_core/stage4.py
scripts/learning.py
schemas/session.schema.yaml
.agents/skills/resume-session/SKILL.md
tests/test_stage4.py
```

Если фактическая структура проекта требует других файлов, адаптируй решение.

## `recover_session`

Расширь recovery так, чтобы оно могло принимать optional reconstructed checkpoint для случая, когда сохранённого checkpoint нет.

Поведение должно быть:

```text
existing checkpoint:
    close_at = checkpoint.updated_at
    recovery source = checkpoint

no existing checkpoint + reconstructed checkpoint:
    close_at = old segment.started_at
    recovery source = segment_start

no existing checkpoint + no reconstructed checkpoint:
    fail and require user input
```

После закрытия старого segment:

```text
open new segment at recovered_at
apply reconstructed checkpoint to new segment if needed
```

Не записывай reconstructed checkpoint в stale segment до его закрытия.

## Recovery metadata

Сделай `last_recovery` честно отражающим источник времени закрытия segment.

Желательная модель:

```yaml
last_recovery:
  recovered_at: ...
  segment_closed_at: ...
  source: checkpoint | segment_start
```

Если текущая schema использует другое поле вроде `checkpoint_at`, обнови её.

## CLI

Расширь `recover-session`, чтобы при необходимости можно было передать reconstructed checkpoint из YAML-файла.

Например концептуально:

```bash
python3 scripts/learning.py recover-session <session-id> \
  --minutes 20 \
  --checkpoint <checkpoint-file>
```

Точное CLI API можешь адаптировать к текущему стилю проекта.

## Skill

Обнови `.agents/skills/resume-session/SKILL.md`.

Важно:

* если checkpoint существует — обычный recovery;
* если checkpoint отсутствует — сначала спросить только semantic state;
* не просить пользователя оценивать elapsed time;
* не вызывать обычный `update-checkpoint` на stale segment перед recovery;
* reconstructed checkpoint должен попасть уже в новый segment.

## Tests

Добавь/обнови тесты минимум для следующих случаев.

### Existing checkpoint

```text
segment started 10:00
checkpoint 10:08
recovery 18:00

old segment ended_at = 10:08
source = checkpoint
```

### No checkpoint

```text
segment started 10:00
no checkpoint
recovery next day 09:00
reconstructed semantic state supplied

old segment ended_at = 10:00
new segment started_at = next day 09:00
checkpoint.updated_at = next day 09:00
source = segment_start
unknown active time is not counted
```

### No checkpoint and no reconstructed state

Recovery must refuse and require user input.

### Idempotency

Repeated recovery must not:

* create duplicate segments;
* duplicate checkpoint state;
* inflate active time.

## Constraints

Не меняй следующие решения Stage 4:

* только одна unfinished Session (`active` или `paused`) на repository;
* `paused` относится только к Session;
* checkpoint обновляется после meaningful steps;
* time budget является planning constraint, а не hard timer;
* pause остаётся ручной операцией;
* active Session, найденная в новом context, считается potentially stale;
* Evidence/Assessment/Progress не должны создаваться из-за самого recovery.

Не добавляй новые крупные сущности или migration framework.

Это небольшой hardening fix Stage 4, а не новый Stage.

## Verification

После изменений запусти:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/learning.py validate
```

Если какие-то команды в проекте называются иначе, используй фактические.

В конце дай краткий summary:

1. какие файлы изменены;
2. как теперь работает recovery с checkpoint;
3. как работает recovery без checkpoint;
4. какие тесты добавлены;
5. подтверждение, что все тесты проходят.
