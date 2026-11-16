# SO-101: запись движений рукой

`lerobot-record-from-follower` записывает единственный follower, который двигают
рукой при отключённом удержании. Используется обычный `LeRobotDataset`:
измеренные положения сохраняются в `observation.state` и `action`.
Команд движения и включения удержания рекордер не отправляет.

## Запись

Рука должна быть собрана, откалибрована с `--robot.id=follower`, основание закреплено.
Подключи USB и питание follower 12 В. Поддерживай руку: удержание будет отключено.

```bash
cd /Users/mvsh/Documents/mipt/ccm/in2ro/hard1

pixi run lerobot-record-from-follower \
  --robot.type=so101_follower \
  --robot.port=/dev/tty.usbmodem5B421347581 \
  --robot.id=follower \
  --dataset.repo_id=local/hand-demo \
  --dataset.root=datasets/hand-demo \
  --dataset.single_task="Move the arm by hand" \
  --dataset.fps=20 \
  --dataset.episode_time_s=10 \
  --dataset.num_episodes=1
```

После первого Enter отключается удержание. Задай начальную позу и нажми Enter
ещё раз: начинается непрерывная запись. Медленно двигай рукой робота.
Для первого опыта достаточно небольшого движения одного сустава.

| Клавиша | Действие |
| --- | --- |
| `n` / → | Закончить эпизод досрочно; во время reset — закончить паузу |
| `r` / ← | Отбросить текущий эпизод и записать его заново |
| `q` / Esc | Сохранить текущий непустой эпизод и выйти |
| Ctrl+C | Прервать; незавершённый эпизод не сохраняется |

Эпизоды нумеруются с нуля. По умолчанию запись локальная, без камер и загрузки
на Hub. Для следующей сессии укажи новые `repo_id` и `root`: существующая папка
не перезаписывается. Имя датасета сохраняется как задано, без добавления даты.

Поддерживаются `--robot.*` для SO-101 и параметры `--dataset.repo_id`, `root`,
`single_task`, `fps`, `episode_time_s`, `reset_time_s`, `num_episodes`,
`push_to_hub` (по умолчанию `false`). Это небольшой рекордер без камер,
resume и визуализации. Углы пяти суставов — в градусах по умолчанию,
захват — в процентах диапазона калибровки.

## Штатное воспроизведение

Сначала вручную верни руку в начальную позу при отключённом удержании.
Освободи её путь и убери руки. Штатный replay может сразу перейти к первому
кадру: плавный подход из произвольной позы он не планирует.
При завершении и Ctrl+C удержание отключается — рука может опуститься.

```bash
pixi run lerobot-replay \
  --robot.type=so101_follower \
  --robot.port=/dev/tty.usbmodem5B421347581 \
  --robot.id=follower \
  --dataset.repo_id=local/hand-demo \
  --dataset.root=datasets/hand-demo \
  --dataset.episode=0 \
  --play_sounds=false
```

Используй ту же калибровку и `--robot.use_degrees`, что при записи.
`lerobot-replay` читает частоту из датасета.

## Проверка

```bash
pixi run python -m unittest discover -s tests -v
```

Проверяются реальное сохранение и чтение датасета, воспроизведение штатным
`lerobot-replay` с подменённым роботом, горячие клавиши и закрытие ресурсов.
Физическое оборудование тесты не открывают.

## Источники

- [Официальные запись и replay](https://huggingface.co/docs/lerobot/v0.7.0/il_robots).
- [API LeRobotDataset v0.7.0](https://github.com/huggingface/lerobot/blob/v0.7.0/src/lerobot/datasets/lerobot_dataset.py).
- [Штатный рекордер: структура данных и управление эпизодами](https://github.com/huggingface/lerobot/blob/v0.7.0/src/lerobot/scripts/lerobot_record.py).
- [Штатный replay: чтение action из эпизода](https://github.com/huggingface/lerobot/blob/v0.7.0/src/lerobot/scripts/lerobot_replay.py).
- [Управление моторами и torque](https://github.com/huggingface/lerobot/blob/v0.7.0/src/lerobot/motors/motors_bus.py).
