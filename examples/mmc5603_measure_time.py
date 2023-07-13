# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

import time
from machine import Pin, I2C
from micropython_mmc5603 import mmc5603

i2c = I2C(1, sda=Pin(2), scl=Pin(3))  # Correct I2C pins for RP2040
mmc = mmc5603.MMC5603(i2c)

mmc.measure_time = mmc5603.MT_3_5ms

while True:
    for measure_time in mmc5603.measure_time_values:
        print("Current Measure time setting: ", mmc.measure_time)
        for _ in range(10):
            magx, magy, magz = mmc.magnetic
            print(f"X:{magx:.2f}, Y:{magy:.2f}, Z:{magz:.2f} uT")
            print()
            time.sleep(0.5)
        mmc.measure_time = measure_time
