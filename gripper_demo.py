"""Move the gripper a little and back, leaving the other joints unpowered."""

import argparse
import math
import time

from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig


def move(bus, start, end):
    for step in range(61):
        blend = (1 - math.cos(math.pi * step / 60)) / 2
        bus.write("Goal_Position", "gripper", start + (end - start) * blend)
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port")
    args = parser.parse_args()

    robot = SO101Follower(SO101FollowerConfig(port=args.port, id="follower"))
    bus = robot.bus
    bus.connect()
    try:
        bus.disable_torque()
        if not bus.is_calibrated:
            raise RuntimeError("Сначала откалибруй follower с --robot.id=follower.")

        bus.set_operating_mode("position", "gripper")
        bus.write("P_Coefficient", "gripper", robot.config.position_p_coefficient)
        bus.write("I_Coefficient", "gripper", robot.config.position_i_coefficient)
        bus.write("D_Coefficient", "gripper", robot.config.position_d_coefficient)
        bus.write("Max_Torque_Limit", "gripper", 500)
        bus.write("Protection_Current", "gripper", 250)
        bus.write("Overload_Torque", "gripper", 25)

        input("Уложи руку устойчиво, освободи захват и убери руки. Enter — начать, Ctrl+C — выйти: ")
        start = bus.read("Present_Position", "gripper")
        target = start + 10 if start <= 80 else start - 10
        print(f"Захват: {start:.1f} → {target:.1f} → {start:.1f} (% диапазона)")
        bus.write("Goal_Position", "gripper", start)
        bus.enable_torque("gripper")
        move(bus, start, target)
        time.sleep(0.5)
        move(bus, target, start)
    finally:
        bus.disconnect()

    print("Готово. Удержание отключено.")


if __name__ == "__main__":
    main()
