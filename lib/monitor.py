#!/usr/bin/python
import atexit
import os
import RPi.GPIO as GPIO
import signal
import sys
import threading
import time

from ConfigParser import ConfigParser

from luma.oled.device import sh1106
from luma.oled.device import ssd1306
from luma.core.serial import i2c

from screens import CpuScreen
from screens import NetworkScreen
from screens import MemoryScreen


class RpiMonitor:
    def __init__(self):
        self.device = None
        self.screens = []
        self.screen_index = 0
        self.threads = []
        self.lock = threading.Lock()
        self.timestamp = None
        self.timer = None
        self.config = ConfigParser()

        self.init()
        self.SCREEN_NEXT_PIN = self.config.getint('buttons', 'pin_next')
        self.SCREEN_PREV_PIN = self.config.getint('buttons', 'pin_previous')
        self.SCREEN_UP_PIN = self.config.getint('buttons', 'pin_up')
        self.SCREEN_DOWN_PIN = self.config.getint('buttons', 'pin_down')
        self.SCREEN_RESET_PIN = self.config.getint('buttons', 'pin_reset')
        self.BUTTON_RESET_TIMEOUT = self.config.getfloat('buttons', 'reset_timeout')
        self.BUTTON_DEBOUNCE_TIME = self.config.getfloat('buttons', 'debounce_time')

    def register(self, screen, index=None):

        thread = threading.Thread(target=screen.collect, args=())
        thread.daemon = True
        thread.start()

        if index is not None:
            self.screens.insert(index, screen)
            self.threads.insert(index, thread)
        else:
            self.screens.append(screen)
            self.threads.append(thread)

    def handle_screen_change(self, channel):
        time_now = time.time()

        if (time_now - self.timestamp) > self.BUTTON_DEBOUNCE_TIME:
            if channel == self.SCREEN_NEXT_PIN:
                self.screen_index = self.screen_index + 1 if self.screen_index + 1 < len(self.screens) else 0
            elif channel == self.SCREEN_PREV_PIN:
                self.screen_index = self.screen_index - 1 if self.screen_index - 1 >= 0 else len(self.screens) - 1
            elif channel == self.SCREEN_UP_PIN:
                self.screens[self.screen_index].next_screen()
            elif channel == self.SCREEN_DOWN_PIN:
                self.screens[self.screen_index].previous_screen()

            if channel in (self.SCREEN_NEXT_PIN, self.SCREEN_PREV_PIN, self.SCREEN_UP_PIN, self.SCREEN_DOWN_PIN):
                self.render()

            self.timestamp = time_now

    def handle_screen_reset_timer_callback(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None
            self.screen_index = 0

            # Reset all screens to their default display
            for screen in self.screens:
                screen.reset_screen()

            self.render()

    def handle_screen_reset(self, channel):
        if GPIO.input(self.SCREEN_RESET_PIN) and self.timer:
            self.timer.cancel()
            self.timer = None

            self.screens[self.screen_index].reset_screen()
            self.render()

        elif not GPIO.input(self.SCREEN_RESET_PIN) and not self.timer:
            self.timer = threading.Timer(self.BUTTON_RESET_TIMEOUT, self.handle_screen_reset_timer_callback)
            self.timer.start()

    def render(self):
        self.lock.acquire()

        try:
            self.screens[self.screen_index].render(self.device)
        finally:
            self.lock.release()

    def shutdown_hook(self):
        self.device.clear()
        self.device.cleanup()

        GPIO.cleanup()

    def setup_gpio_pin(self, pin, action):
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(pin, GPIO.BOTH)
        GPIO.add_event_callback(pin, action)

    def init(self):
        config_locations = [
            '/usr/local/pi-monitor/etc/config.cfg',
            os.path.expanduser('~/.pi-monitor/config.cfg')
        ]

        for config_location in config_locations:
            self.load_config(config_location)

    def load_config(self, path):
        if os.path.exists(path):
            print 'Loading config: %s' % path
            self.config.read(path)

    def run(self):
        print 'Setting up GPIO'
        GPIO.setmode(GPIO.BCM)

        self.setup_gpio_pin(self.SCREEN_NEXT_PIN, self.handle_screen_change)
        self.setup_gpio_pin(self.SCREEN_PREV_PIN, self.handle_screen_change)
        self.setup_gpio_pin(self.SCREEN_UP_PIN, self.handle_screen_change)
        self.setup_gpio_pin(self.SCREEN_DOWN_PIN, self.handle_screen_change)
        self.setup_gpio_pin(self.SCREEN_RESET_PIN, self.handle_screen_reset)

        print 'Setting up display'
        serial = i2c(port=self.config.getint('display', 'port'), address=int(self.config.get('display', 'address'), 16))

        self.device = ssd1306(serial)

        if 'sh1106' == self.config.get('display', 'driver'):
            self.device = sh1106(serial)

        self.register(CpuScreen())

        for iface in [item.strip() for item in self.config.get('network', 'iface').split(',')]:
            self.register(NetworkScreen(iface))

        self.register(MemoryScreen())

        signal.signal(signal.SIGTERM, lambda num, frame: sys.exit(0))
        atexit.register(self.shutdown_hook)

        self.timestamp = time.time()

        while True:
            screen = self.screens[self.screen_index]
            self.render()
            time.sleep(screen.sleep_interval())


if __name__ == '__main__':
    try:
        monitor = RpiMonitor()
        monitor.run()
    except KeyboardInterrupt:
        print 'Shutting down monitor'
        sys.exit(0)
