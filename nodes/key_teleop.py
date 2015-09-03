#! /usr/bin/env python
# -*- coding: utf-8 -*-
#

import curses
import math

import rospy
from geometry_msgs.msg import Twist

class TextWindow():

    _screen = None
    _window = None
    _num_lines = None

    def __init__(self, stdscr, lines=10):
        self._screen = stdscr
        self._screen.nodelay(True)
        curses.curs_set(0)

        self._num_lines = lines

    def read_key(self):
        keycode = self._screen.getch()
        return keycode if keycode != -1 else None

    def clear(self):
        self._screen.clear()

    def write_line(self, lineno, message):
        if lineno < 0 or lineno >= self._num_lines:
            raise ValueError, 'lineno out of bounds'
        height, width = self._screen.getmaxyx()
        y = (height / self._num_lines) * lineno
        x = 10
        for text in message.split('\n'):
            text = text.ljust(width)
            self._screen.addstr(y, x, text)
            y += 1

    def refresh(self):
        self._screen.refresh()

    def beep(self):
        curses.flash()

class KeyTeleop():
    def __init__(self, interface):
        self._interface = interface
        self._pub_cmd = rospy.Publisher('key_vel', Twist)

        self._hz = rospy.get_param('~hz', 10)

        self._x_positive_rate = rospy.get_param('~x_positive_rate', 1000)
        self._x_negative_rate = rospy.get_param('~x_negative_rate', -1000)
        self._y_positive_rate = rospy.get_param('~y_positive_rate', 1000)
        self._y_negative_rate = rospy.get_param('~y_negative_rate', -1000)
        self._last_pressed = {}
        self._x_rate = 0
        self._y_rate = 0

    movement_bindings = {
        curses.KEY_UP:    ( 1,  0),
        curses.KEY_DOWN:  (-1,  0),
        curses.KEY_LEFT:  ( 0,  1),
        curses.KEY_RIGHT: ( 0, -1),
    }

    def run(self):
        rate = rospy.Rate(self._hz)
        self._running = True
        while self._running:
            while True:
                keycode = self._interface.read_key()
                if keycode is None:
                    break
                self._key_pressed(keycode)
                self._set_velocity()
                self._publish()
                rate.sleep()

    def _get_twist(self, x_rate, y_rate):
        twist = Twist()
        twist.linear.x = x_rate
        twist.linear.y = y_rate
        return twist

    def _set_velocity(self):
        now = rospy.get_time()
        keys = []
        for a in self._last_pressed:
            if now - self._last_pressed[a] < 0.4:
                keys.append(a)
        x_rate = 0
        y_rate = 0
        for k in keys:
            x,y = self.movement_bindings[k]
            x_rate += x
            y_rate += y
        if x_rate > 0:
            x_rate = x_rate * self._x_positive_rate
        else:
            x_rate = x_rate * self._x_negative_rate
        if y_rate > 0:
            y_rate = y_rate * self._x_positive_rate
        else:
            y_rate = y_rate * self._x_negative_rate
        self._x_rate += x_rate
        self._y_rate += y_rate

    def _key_pressed(self, keycode):
        if keycode == ord('q'):
            self._running = False
            rospy.signal_shutdown('Bye')
        elif keycode in self.movement_bindings:
            self._last_pressed[keycode] = rospy.get_time()

    def _publish(self):
        self._interface.clear()
        self._interface.write_line(2, 'X Rate: %f, Y Rate: %f' % (self._x_rate, self._y_rate))
        self._interface.write_line(5, 'Use arrow keys to move, q to exit.')
        self._interface.refresh()

        twist = self._get_twist(self._linear, self._angular)
        self._pub_cmd.publish(twist)


def main(stdscr):
    rospy.init_node('key_teleop')
    app = KeyTeleop(TextWindow(stdscr))
    app.run()

if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except rospy.ROSInterruptException:
        pass
