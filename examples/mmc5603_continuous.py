# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

import time
from machine import Pin, I2C
from micropython_mmc5603 import mmc5603

i2c = I2C(1, sda=Pin(2), scl=Pin(3))  # Correct I2C pins for RP2040
mmc = mmc5603.MMC5603(i2c)

mmc.data_rate = 10  # in Hz, from 1-255 or 1000
mmc.continuous_mode = True

while True:
    mag_x, mag_y, mag_z = mmc.magnetic
    print(f"X:{mag_x:.2f}, Y:{mag_y:.2f}, Z:{mag_z:.2f} uT")
    print()
    time.sleep(0.5)
