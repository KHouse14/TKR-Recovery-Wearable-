import math
import random
import time
import board
import busio
import adafruit_lsm9ds1

from adafruit_debouncer import Debouncer

import digitalio
from digitalio import DigitalInOut, Direction, Pull
import storage
import adafruit_sdcard

import serverlib
from serverlib import spi
from serverlib import esp
from adafruit_esp32spi import adafruit_esp32spi

dataString = ""

file_path = "static/"
file_name = "index.html"

fp = open(file_path + file_name, "w")

def hello(environ):
    print("executed")
    return serverlib.getFile(file_name)

def testing(environ):
    print("Testing value")
    return ("200 OK", [], [dataString])


serverlib.register("GET", "/", hello)
serverlib.register("GET", "/test", testing)

#SPI connection:
from digitalio import DigitalInOut, Direction
#spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
csag = DigitalInOut(board.D42)
csag.direction = Direction.OUTPUT
csag.value = True
csm = DigitalInOut(board.D44)
csm.direction = Direction.OUTPUT
csm.value = True
sensor1 = adafruit_lsm9ds1.LSM9DS1_SPI(spi, csag, csm)

#shin = 1, thigh = 2
csag2 = DigitalInOut(board.D59)
csag2.direction = Direction.OUTPUT
csag2.value = True
csm2 = DigitalInOut(board.D49)
csm2.direction = Direction.OUTPUT
csm2.value = True
sensor2 = adafruit_lsm9ds1.LSM9DS1_SPI(spi, csag2, csm2)

accel_angle = 0
prev_accel_angle = 0
saved_accel_angle = 0
inter = 0.1
seconds_since_start = 0
shin_vert_angle = 0

steps = 0
amount_y_off = 0.775
drift = 0.13
gyro_angle = 0
gravity = 9.8
compression_shin = 0

real_angle = 0
count = 0
add = False
saved = False
not_calibrated = True
flush_counter = 0
mass = 84 #kg

html_body = """"""

while True:
    serverlib.poll()
    print("polling")
    accel_x1, accel_y1, accel_z1 = sensor1.acceleration
    accel_x2, accel_y2, accel_z2 = sensor2.acceleration

    gyro_x1, gyro_y1, gyro_z1 = sensor1.gyro
    gyro_x2, gyro_y2, gyro_z2 = sensor2.gyro

    #Acceleration angle of knee
    scalar_shin = math.sqrt(math.pow(accel_z1, 2) + math.pow(accel_x1, 2) + math.pow(accel_y1, 2))
    scalar_thigh = math.sqrt(math.pow(accel_z2, 2) + math.pow(accel_x2, 2) + math.pow(accel_y2, 2))
    dot_product = (accel_z1 * accel_z2) + (accel_x1 * accel_x2) + (accel_y1 * accel_y2)
    magnitude_product = (scalar_shin * scalar_thigh)
    if magnitude_product == 0:
        magnitude_product = 0.01
    accel_angle = math.acos(dot_product / magnitude_product)
    accel_angle = 180 - math.degrees(accel_angle)

    #Gyro angle of knee
    if steps == 0:
        gyro_angle = accel_angle
    else:
        steps += 1
        angular_vel_1 = gyro_y1 + (amount_y_off)
        angular_vel_2 = gyro_y2 + (amount_y_off)
        gyro_angle = accel_angle + (angular_vel_1 * inter) - (angular_vel_2 * inter)
        gyro_angle -= drift

    #Real angle of knee during impacts/jolts
    if (prev_accel_angle * 0.85 > accel_angle) and (steps > 0) :
        add = True
        saved = True
        saved_accel_angle = prev_accel_angle
    else:
        real_angle = (gyro_angle + accel_angle) / 2

    if saved and add:
        saved_accel_angle = prev_accel_angle
        angular_vel_1 = gyro_y1 + (amount_y_off)
        angular_vel_2 = gyro_y2 + (amount_y_off)
        delta_theta = (angular_vel_1 * inter) - (angular_vel_2 * inter)
        real_angle = saved_accel_angle + delta_theta - drift
        saved = False
        count += 1
    elif add:
        count += 1

    if count == 4:
        gyro_angle = accel_angle
        real_angle = accel_angle
        count = 0
        add = False
        saved_accel_angle = 0

    prev_accel_angle = accel_angle


    g_force_thigh = accel_x2 / gravity
    force_thigh = mass * g_force_thigh
    print((g_force_thigh,))


    seconds_since_start += inter

    dataString += "<p> Time: " + str(math.ceil(seconds_since_start)) + "s || g-force: " + str(g_force_thigh) + " || Angle: " + str(real_angle) + "</p>"

    if flush_counter == 75:
        dataString = ""
        flush_counter = 0

    if steps == 0:
        steps += 1

    flush_counter += 1

    time.sleep(inter)
    # Delay for a second.
