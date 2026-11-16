# In2Ro Hard 1

Делаем ДЗ из [In2Ro_hw_hard1.pdf](In2Ro_hw_hard1.pdf) на SO-101 (Seeed Pro).
SO-101 нет в списке задания; замена согласована с преподавателем.

Проект: `/Users/mvsh/Documents/mipt/ccm/in2ro/hard1`.
macOS, Apple Silicon, Pixi, LeRobot 0.7.0. Команды запускать из проекта через `pixi run`.

| Рука | Порт | Имя калибровки | Питание |
|---|---|---|---|
| Follower | `/dev/tty.usbmodem5B421347581` | `--robot.id=follower` | 12 В, C047 |
| Leader | `/dev/tty.usbmodem5B421344761` | `--teleop.id=leader` | 5 В |

Обе руки собраны, ID моторов настроены, откалиброваны. Телеоперация, запись и
воспроизведение проверены: кубик берётся и ставится. Камеры не используем.
Локальные записи: `datasets/repeat-test-01`, `datasets/repeat-test-02`; в Git не входят.
