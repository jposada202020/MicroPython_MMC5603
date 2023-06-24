# SPDX-FileCopyrightText: Copyright (c) 2022 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT
"""
`mmc5603`
================================================================================

MicroPython driver for the Memsic MMC5603 Magnetometer


* Author(s): ladyada, Jose D. Montoya


"""
import struct
import time
from micropython import const
from micropython_mmc5603.i2c_helpers import CBits, RegisterStruct

try:
    from typing import Tuple
except ImportError:
    pass


__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/jposada202020/MicroPython_MMC5603.git"


_REG_WHOIAM = const(0x39)
_DATA = const(0x00)
_TEMP = const(0x09)
_STATUS_REG = const(0x18)
_ODR_REG = const(0x1A)
_CTRL_REG0 = const(0x1B)
_CTRL_REG1 = const(0x1C)
_CTRL_REG2 = const(0x1D)

MT_6_6ms = const(0b00)
MT_3_5ms = const(0b01)
MT_2_0ms = const(0b10)
MT_1_2ms = const(0b11)
measure_time_values = (MT_6_6ms, MT_3_5ms, MT_2_0ms, MT_1_2ms)


class MMC5603:
    """Driver for the MMC5603 Sensor connected over I2C.

    :param ~machine.I2C i2c: The I2C bus the MMC5603 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x30`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`MMC5603` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        from machine import Pin, I2C
        from micropython_mmc5603 import mmc5603

    Once this is done you can define your `machine.I2C` object and define your sensor object

    .. code-block:: python

        i2c = I2C(1, sda=Pin(2), scl=Pin(3))
        mmc = mmc5603.MMC5603(i2c)

    Now you have access to the attributes

    .. code-block:: python

        magx, magy, magz = mmc.magnetic

    """

    _device_id = RegisterStruct(_REG_WHOIAM, "<B")
    _ctrl0_reg = RegisterStruct(_CTRL_REG0, "<B")
    _ctrl1_reg = RegisterStruct(_CTRL_REG1, "<B")
    _ctrl2_reg = RegisterStruct(_CTRL_REG2, "B")

    _odr_reg = RegisterStruct(_ODR_REG, "<B")
    _raw_temp_data = RegisterStruct(_TEMP, "B")

    _meas_m_done = CBits(1, _STATUS_REG, 6)
    _meas_t_done = CBits(1, _STATUS_REG, 7)

    def __init__(self, i2c, address: int = 0x30) -> None:
        self._i2c = i2c
        self._address = address

        if self._device_id != 0x10:
            raise RuntimeError("Failed to find MMC5603")

        self._ctrl2_cache = 0
        self._odr_cache = 0
        self._measure_time_cached = 0

        self._buffer = bytearray(9)
        # self.continuous_mode = False

        self._ctrl1_reg = 0x80
        time.sleep(0.020)
        self._ctrl0_reg = 0x08  # Do_Set
        time.sleep(0.001)
        self._ctrl0_reg = 0x10  # Do_Reset
        time.sleep(0.001)
        self._ctrl0_reg = 0x20  # Set the Do_Set-Do_Reset Automatically
        time.sleep(0.001)

    @property
    def magnetic(self) -> Tuple[float, float, float]:
        """The processed magnetometer sensor values.
        A 3-tuple of X, Y, Z axis values in microteslas that are signed floats.
        """

        if not self.continuous_mode:
            self._ctrl0_reg = 0x01

            while not self._meas_m_done:
                time.sleep(0.005)

        self._i2c.readfrom_mem_into(self._address, _DATA, self._buffer)

        x = self._buffer[0] << 12 | self._buffer[1] << 4 | self._buffer[6] >> 4
        y = self._buffer[2] << 12 | self._buffer[3] << 4 | self._buffer[7] >> 4
        z = self._buffer[4] << 12 | self._buffer[5] << 4 | self._buffer[8] >> 4

        x -= 1 << 19
        y -= 1 << 19
        z -= 1 << 19
        # scale to uT by LSB in datasheet
        x *= 0.00625
        y *= 0.00625
        z *= 0.00625
        return x, y, z

    @property
    def temperature(self) -> float:
        """The processed temperature sensor value, returned in floating point C"""
        if self.continuous_mode:
            raise RuntimeError("Can only read temperature when not in continuous mode")
        self._ctrl0_reg = 0x02

        while not self._meas_t_done:
            time.sleep(0.005)
        temp = self._raw_temp_data
        temp *= 0.8
        temp -= 75
        return temp

    @property
    def data_rate(self) -> int:
        """Output data rate, 0 for on-request data.
        1-255 or 1000 for freq of continuous-mode readings"""
        return self._odr_cache

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        if not ((value == 1000) or (0 <= value <= 255)):
            raise ValueError("Data rate must be 0-255 or 1000 Hz")
        self._odr_cache = value
        if value == 1000:
            self._odr_reg = 255
            self._ctrl2_cache |= 0x80  # turn on hpower bit
            self._ctrl2_reg = self._ctrl2_cache
        else:
            self._odr_reg = value
            self._ctrl2_cache &= ~0x80  # turn off hpower bit
            self._ctrl2_reg = self._ctrl2_cache

    @property
    def continuous_mode(self) -> bool:
        """Whether or not to put the chip in continous mode - be sure
        to set the data_rate as well!
        """
        return self._ctrl2_cache & 0x10

    @continuous_mode.setter
    def continuous_mode(self, value: bool) -> None:
        if value:
            self._ctrl0_reg = 0x80  # turn on cmm_freq_en bit
            self._ctrl2_cache |= 0x10  # turn on cmm_en bit
        else:
            self._ctrl2_cache &= ~0x10  # turn off cmm_en bit

        self._ctrl2_reg = self._ctrl2_cache

    @property
    def measure_time(self) -> str:
        """
        Sensor measure_time adjust the length of the decimation filter.
        They control the duration of each measurement.
        Note: X/Y/Z channel measurements are taken sequentially. Delay Time
        among those measurements is 1/3 of the Measurement

        +------------------------------+------------------+
        | Mode                         | Value            |
        +==============================+==================+
        | :py:const:`mmc5603.MT_6_6ms` | :py:const:`0b00` |
        +------------------------------+------------------+
        | :py:const:`mmc5603.MT_3_5ms` | :py:const:`0b01` |
        +------------------------------+------------------+
        | :py:const:`mmc5603.MT_2_0ms` | :py:const:`0b10` |
        +------------------------------+------------------+
        | :py:const:`mmc5603.MT_1_2ms` | :py:const:`0b11` |
        +------------------------------+------------------+
        """
        values = ("MT_6_6ms", "MT_3_5ms", "MT_2_0ms", "MT_1_2ms")
        return values[self._measure_time_cached]

    @measure_time.setter
    def measure_time(self, value: int) -> None:
        if value not in measure_time_values:
            raise ValueError("Value must be a valid measure_time setting")
        self._ctrl1_reg = value
        self._measure_time_cached = value
