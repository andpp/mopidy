from __future__ import absolute_import, unicode_literals

import logging
import threading
import datetime
#import gobject
import time

from mopidy.audio import PlaybackState
from mopidy.core import playback, listener

logger = logging.getLogger(__name__)


class SleepTimerController(object):
    pykka_traversable = True

    def __init__(self, playback, core):
        logger.debug('Core.SleepTimer __init__')
        self.playback = playback
        self.core = core

        self._cancelevent = threading.Event()
        self._timer = None
        self._state = SleeptimerState()
        self._state.__init__()
        self._timer_id = None

    def get_state(self):
        return {"running": self._state.running,
                "duration": self._state.duration,
                "seconds_left": self._get_seconds_left()}

    def _get_seconds_left(self):
            now = datetime.datetime.now()
            time_left = self._state.timerEndTime - now
            seconds_left = time_left.total_seconds()

            if seconds_left < 0:
                seconds_left = 0

            return seconds_left

    def cancel(self, notify=True):
        logger.debug('Cancel')

        self._cancelevent.set()

        if notify:
            listener.CoreListener.send(
                'sleeptimer_cancelled')

        return True

    def start(self, duration):
        old_state = self._state.running
        logger.debug('Start - state = %s, duration = %d', old_state, duration)

        if self._state.running:
            self.cancel(False)

        self._state.start(duration)

        if self._timer:
             self._timer.cancel()

        #gobject.timeout_add(500, self._tick_handler)
        self._timer=threading.Timer(1, self._tick_handler)
        self._timer.start()

        self._cancelevent.clear()

        listener.CoreListener.send(
            'sleeptimer_started',
            was_running=old_state, duration=self._state.duration, seconds_left=self._get_seconds_left())

        return True

    def _tick_handler(self):
        logger.debug('tick_handler, time left = %s', self._get_seconds_left())

        if self._cancelevent.is_set():
            return False

        if datetime.datetime.now() > self._state.timerEndTime:
            self._cancelevent.set()

            if self.playback.get_state() != PlaybackState.STOPPED:
                #self.playback.stop()
                self.playback.pause()

            listener.CoreListener.send(
                'sleeptimer_expired')

            self._state.clear()

            return False
        else:
            self._timer=threading.Timer(1, self._tick_handler)
            self._timer.start()
            listener.CoreListener.send(
                'sleeptimer_tick',
                seconds_left=self._get_seconds_left())

            return True


class SleeptimerState(object):
    pykka_traversable = True

    def __init__(self):
        #self.running = False
        #self.duration = 0
        self.clear()

    def clear(self):
        self.running = False
        self.timerStartTime = datetime.datetime.now() 
        self.timerEndTime = self.timerStartTime
        self.duration = 0

    def start(self, duration):
        self.running = True
        self.timerStartTime = datetime.datetime.now()
        self.timerEndTime = self.timerStartTime + datetime.timedelta(seconds=duration)
        self.duration = duration

        logger.debug('SleepTimerState.start: running = %s, end time = %s', self.running, self.timerEndTime)
