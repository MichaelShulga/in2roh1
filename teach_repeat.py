"""Teach two nearby poses by hand and replay them once."""

import argparse
import json
import math
from pathlib import Path
import time

from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig


def check_step(start, end):
    for motor in start:
        limit = 20 if motor == "gripper" else 15
        if abs(end[motor] - start[motor]) > limit:
            raise ValueError(f"Слишком большое движение {motor}. Для первого теста задай позы ближе.")


def move(bus, start, end):
    for step in range(81):
        blend = (1 - math.cos(math.pi * step / 80)) / 2
        bus.sync_write("Goal_Position", {
            motor: start[motor] + (end[motor] - start[motor]) * blend
            for motor in start
        })
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port")
    args = parser.parse_args()

    robot = SO101Follower(SO101FollowerConfig(port=args.port, id="follower"))
    bus = robot.bus
    input("Закрепи основание и поддержи руку: сейчас удержание отключится. Enter — продолжить: ")
    bus.connect()
    try:
        bus.disable_torque()
        if not bus.is_calibrated:
            raise RuntimeError("Сначала откалибруй follower с --robot.id=follower.")

        bus.set_operating_mode("position")
        for motor in bus.motors:
            bus.write("P_Coefficient", motor, robot.config.position_p_coefficient)
            bus.write("I_Coefficient", motor, robot.config.position_i_coefficient)
            bus.write("D_Coefficient", motor, robot.config.position_d_coefficient)
        bus.write("Max_Torque_Limit", "gripper", 500)
        bus.write("Protection_Current", "gripper", 250)
        bus.write("Overload_Torque", "gripper", 25)

        poses = []
        for number in (1, 2):
            input(f"Задай и держи позу {number}. Enter — записать: ")
            pose = bus.sync_read("Present_Position", num_retry=robot.config.num_read_retries)
            poses.append(pose)
            print({motor: round(value, 1) for motor, value in pose.items()})
        check_step(poses[0], poses[1])

        path = Path(__file__).with_name("poses.json")
        path.write_text(json.dumps({
            "units": {"joints": "degrees", "gripper": "percent"},
            "poses": poses,
        }, indent=2) + "\n")
        print("Позы сохранены:", path)

        input("Продолжай держать вторую позу. Enter — включить удержание: ")
        current = bus.sync_read("Present_Position", num_retry=robot.config.num_read_retries)
        check_step(current, poses[0])
        check_step(current, poses[1])
        for motor, value in current.items():
            bus.write("Goal_Position", motor, value)
        bus.enable_torque()

        input("Удержание включено. Убери руки и освободи путь. Enter — движение 1 → 2: ")
        move(bus, current, poses[0])
        time.sleep(1)
        move(bus, poses[0], poses[1])
        input("Готово. Поддержи руку. Enter — отключить удержание и выйти: ")
    finally:
        bus.disconnect()

    print("Удержание отключено.")


if __name__ == "__main__":
    main()
