"""Record hand-guided SO-101 motion for the standard lerobot-replay command."""

from contextlib import ExitStack
from dataclasses import dataclass
import logging
from pathlib import Path
import time

import draccus

from lerobot.datasets import LeRobotDataset
from lerobot.robots import RobotConfig
from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
from lerobot.utils.cycle_timer import CycleTimer
from lerobot.utils.feature_utils import build_dataset_frame, hw_to_dataset_features
from lerobot.utils.keyboard_input import init_keyboard_listener
from lerobot.utils.utils import init_logging


@dataclass
class DatasetConfig:
    repo_id: str
    single_task: str
    root: Path | None = None
    fps: int = 30
    episode_time_s: float = 20
    reset_time_s: float = 5
    num_episodes: int = 1
    push_to_hub: bool = False

    def __post_init__(self):
        if min(self.fps, self.episode_time_s, self.num_episodes) <= 0 or self.reset_time_s < 0:
            raise ValueError("fps, episode_time_s and num_episodes must be positive; reset_time_s >= 0.")


@dataclass
class RecordConfig:
    robot: RobotConfig
    dataset: DatasetConfig

    def __post_init__(self):
        if not isinstance(self.robot, SO101FollowerConfig) or self.robot.cameras:
            raise ValueError("This recorder supports an SO-101 follower without cameras.")


def record_episode(robot, dataset, cfg, events):
    timer = CycleTimer(cfg.fps)
    start = time.perf_counter()
    try:
        while time.perf_counter() - start < cfg.episode_time_s and not events["exit_early"]:
            timer.tick()
            with timer.section("observe"):
                positions = robot.bus.sync_read(
                    "Present_Position", num_retry=robot.config.num_read_retries
                )
                observation = {f"{motor}.pos": value for motor, value in positions.items()}
            with timer.section("record"):
                dataset.add_frame({
                    **build_dataset_frame(dataset.features, observation, "observation"),
                    **build_dataset_frame(dataset.features, observation, "action"),
                    "task": cfg.single_task,
                })
            timer.wait()
    finally:
        timer.log_run_summary()


def reset_scene(seconds, events):
    events["exit_early"] = False
    start = time.perf_counter()
    while time.perf_counter() - start < seconds and not events["exit_early"]:
        time.sleep(0.05)


@draccus.wrap()
def record(cfg: RecordConfig):
    init_logging()
    robot = SO101Follower(cfg.robot)
    features = {
        **hw_to_dataset_features(robot.observation_features, "observation", use_video=False),
        **hw_to_dataset_features(robot.action_features, "action", use_video=False),
    }

    input("Закрепи основание и поддержи руку. Enter — подключиться и отключить удержание: ")
    with ExitStack() as stack:
        robot.bus.connect()
        stack.callback(robot.bus.disconnect)
        robot.bus.disable_torque()
        if not robot.bus.is_calibrated:
            raise RuntimeError("Calibrate this robot.id before recording.")

        dataset = LeRobotDataset.create(
            repo_id=cfg.dataset.repo_id,
            root=cfg.dataset.root,
            fps=cfg.dataset.fps,
            robot_type=robot.robot_type,
            features=features,
            use_videos=False,
        )
        stack.callback(dataset.finalize)
        input("Задай начальную позу. Enter — начать запись движений рукой: ")
        listener, events = init_keyboard_listener()
        if listener is not None:
            stack.callback(listener.stop)

        while dataset.num_episodes < cfg.dataset.num_episodes and not events["stop_recording"]:
            events["exit_early"] = False
            logging.info("Recording episode %d. n/→: finish, r/←: retry, q/Esc: save and quit.", dataset.num_episodes)
            record_episode(robot, dataset, cfg.dataset, events)

            if not events["stop_recording"] and (
                dataset.num_episodes < cfg.dataset.num_episodes - 1 or events["rerecord_episode"]
            ):
                logging.info("Reset: %.1f seconds. Return the arm by hand; n/→: start now.", cfg.dataset.reset_time_s)
                reset_scene(cfg.dataset.reset_time_s, events)

            if events["rerecord_episode"]:
                dataset.clear_episode_buffer()
                events["rerecord_episode"] = False
                logging.info("Episode discarded.")
            elif dataset.has_pending_frames():
                dataset.save_episode()
                logging.info("Saved episode %d.", dataset.num_episodes - 1)

    print(f"Saved {dataset.num_episodes} episode(s): {dataset.root}")
    if cfg.dataset.push_to_hub and dataset.num_episodes:
        dataset.push_to_hub()


if __name__ == "__main__":
    record()
