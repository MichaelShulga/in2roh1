from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import draccus
import numpy as np

from lerobot.datasets import LeRobotDataset, LeRobotDatasetMetadata
from lerobot.robots.so_follower import SO101FollowerConfig
from lerobot.scripts import lerobot_replay

import record_from_follower as recorder


MOTORS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")


class Bus:
    is_calibrated = True

    def __init__(self, events, controls=None):
        self.events = events
        self.controls = controls or {}
        self.frames = 0
        self.connected = False
        self.torque_disabled = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def disable_torque(self):
        self.torque_disabled = True

    def sync_read(self, register, **kwargs):
        assert self.torque_disabled
        self.frames += 1
        control = self.controls.get(self.frames)
        if control == "interrupt":
            raise KeyboardInterrupt
        if control:
            self.events["exit_early"] = True
            self.events[control] = True
        return {motor: float(index + self.frames) for index, motor in enumerate(MOTORS)}

    def enable_torque(self, *args, **kwargs):
        raise AssertionError("Recorder must never enable torque")

    def write(self, *args, **kwargs):
        raise AssertionError("Recorder must never send position commands")

    sync_write = write


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "recording"
        self.events = dict(exit_early=False, rerecord_episode=False, stop_recording=False)
        self.listener = SimpleNamespace(stop=lambda: setattr(self, "listener_stopped", True))
        self.listener_stopped = False
        self.config = recorder.RecordConfig(
            robot=SO101FollowerConfig(port="MOCK", id="follower"),
            dataset=recorder.DatasetConfig(
                repo_id="local/test", single_task="Move by hand", root=self.root,
                fps=20, episode_time_s=0.11, reset_time_s=0, num_episodes=2,
            ),
        )

    def run_recording(self, controls=None):
        self.bus = Bus(self.events, controls)
        robot = SimpleNamespace(
            bus=self.bus, config=self.config.robot, robot_type="so_follower",
            observation_features={f"{motor}.pos": float for motor in MOTORS},
            action_features={f"{motor}.pos": float for motor in MOTORS},
        )
        with patch.object(recorder, "SO101Follower", return_value=robot), patch.object(
            recorder, "init_keyboard_listener", return_value=(self.listener, self.events)
        ), patch("builtins.input", return_value=""), patch.object(recorder, "init_logging"):
            recorder.record.__wrapped__(self.config)

    def test_standard_replay_reads_and_replays_recorded_episode(self):
        self.run_recording()
        self.assertFalse(self.bus.connected)
        self.assertTrue(self.listener_stopped)
        dataset = LeRobotDataset("local/test", root=self.root, episodes=[0])
        self.assertEqual(dataset.num_episodes, 1)
        all_episodes = LeRobotDataset("local/test", root=self.root)
        self.assertEqual(all_episodes.num_episodes, 2)
        self.assertEqual(dataset.features["action"]["names"], [f"{motor}.pos" for motor in MOTORS])
        self.assertEqual(dataset.meta.video_keys, [])
        actions = dataset.select_columns("action")
        for index in range(dataset.num_frames):
            np.testing.assert_array_equal(dataset[index]["observation.state"], actions[index]["action"])

        sent = []
        connected = []
        robot = SimpleNamespace(
            connect=lambda: connected.append(True),
            disconnect=lambda: connected.append(False),
            get_observation=lambda: dict.fromkeys((f"{motor}.pos" for motor in MOTORS), 0.0),
            send_action=lambda action: sent.append(action),
        )
        cfg = lerobot_replay.ReplayConfig(
            robot=self.config.robot,
            dataset=lerobot_replay.DatasetReplayConfig(repo_id="local/test", root=self.root, episode=0),
            play_sounds=False,
        )
        with patch.object(lerobot_replay, "make_robot_from_config", return_value=robot), patch.object(
            lerobot_replay, "init_logging"
        ):
            lerobot_replay.replay.__wrapped__(cfg)
        self.assertEqual(connected, [True, False])
        self.assertEqual(len(sent), dataset.num_frames)
        for index, action in enumerate(sent):
            np.testing.assert_array_equal(list(action.values()), actions[index]["action"])

    def test_retry_discards_episode_and_quit_saves_partial_episode(self):
        self.run_recording({1: "rerecord_episode", 3: "stop_recording"})
        dataset = LeRobotDataset("local/test", root=self.root)
        self.assertEqual(dataset.num_episodes, 1)
        self.assertEqual(dataset.num_frames, 2)
        self.assertEqual(float(dataset[0]["action"][0]), 2.0)
        self.assertFalse(self.bus.connected)
        self.assertTrue(self.listener_stopped)

    def test_interrupt_closes_resources_and_does_not_save_partial_episode(self):
        with self.assertRaises(KeyboardInterrupt):
            self.run_recording({2: "interrupt"})
        self.assertFalse(self.bus.connected)
        self.assertTrue(self.listener_stopped)
        metadata = LeRobotDatasetMetadata("local/test", root=self.root)
        self.assertEqual(metadata.total_episodes, 0)

    def test_lerobot_style_arguments(self):
        cfg = draccus.parse(recorder.RecordConfig, args=[
            "--robot.type=so101_follower", "--robot.port=MOCK", "--robot.id=follower",
            "--dataset.repo_id=local/hand-demo", "--dataset.single_task=Move by hand",
            "--dataset.root=datasets/hand-demo", "--dataset.fps=20",
            "--dataset.num_episodes=1", "--dataset.episode_time_s=10",
        ])
        self.assertIsInstance(cfg.robot, SO101FollowerConfig)
        self.assertTrue(cfg.robot.use_degrees)
        self.assertEqual(cfg.dataset.root, Path("datasets/hand-demo"))
        self.assertFalse(cfg.dataset.push_to_hub)


if __name__ == "__main__":
    unittest.main()
