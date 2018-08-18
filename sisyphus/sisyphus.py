#! /usr/bin/env python
# Copyright (C) 2018-2018 cmj<cmj@cmj.tw>. All right reserved.

import time
import logging
import setproctitle # pylint: disable=import-error
from multiprocessing import Process
import subprocess
import sys


class Sisyphus(object):
    _jobs_ = {}

    def __init__(self, debug=False, monitor_freq=1):
        fmt = '[%(asctime)-.19s] (%(filename)s#%(lineno)04d) - %(message)s'
        fmt = logging.Formatter(fmt)

        syslog = logging.StreamHandler()
        syslog.setFormatter(fmt)

        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.DEBUG if debug else logging.WARNING)

        if not logger.handlers:
            logger.addHandler(syslog)
        logger = logging.LoggerAdapter(logger, {'app_name': self.__class__.__name__})

        for attr in 'critical error warning info debug'.split():
            setattr(self, attr, getattr(logger, attr))

        Sisyphus.remove('_monitor')
        if monitor_freq != 0:
            self._register_monitor(monitor_freq)

    def __call__(self, frequency=5):
        jobs = {}
        try:
            while True:
                for name in self._jobs_:
                    if name not in jobs or not jobs[name].is_alive():
                        jobs[name] = Process(target=self.worker, args=(name, ))
                        jobs[name].start()
                        self.warning(f'new job `{name}` on PID#{jobs[name].pid}')
                time.sleep(frequency)
        except KeyboardInterrupt:
            for name in self._jobs_:
                if name in jobs and jobs[name].is_alive():
                    _ = jobs[name].kill() if hasattr(jobs[name], 'kill') else jobs[name].terminate()
            self.critical(f'Ctrl-C')

    def worker(self, name):
        setproctitle.setproctitle(f'{name} ({self._jobs_[name]["frequency"]})')
        while True:
            self._jobs_[name]['fn'].__globals__['worker'] = self
            self._jobs_[name]['fn']()
            time.sleep(self._jobs_[name]['frequency'])

    def _register_monitor(self, frequency=1):
        def my_monitor():
            ps_pipe = subprocess.Popen(['ps', 'a'], stdout=subprocess.PIPE)
            stdout, stderr = ps_pipe.communicate()
            if stderr:
                print(f'error: {stderr}')
                return

            cmd_lines = [' '.join(_.split()[4:]) for _ in stdout.decode('ascii').split('\n')[1:]]
            for name, v in Sisyphus._jobs_.items():
                process_name = f'{name} ({v["frequency"]})'
                if name == '_monitor':
                    continue
                if any([process_name == _ for _ in cmd_lines]):
                    print(f"m (Running): '{process_name}'")

        self._jobs_['_monitor'] = {'fn': my_monitor, 'frequency': frequency}

    @property
    def jobs(self):
        jobs = [f'- {job} ({item["fn"]})' for job, item in self._jobs_.items()]
        return '\n'.join(jobs)

    @classmethod
    def register(cls, frequency=1):
        def wrapper(func):
            if func.__name__ in cls._jobs_:
                raise KeyError(func.__name__)

            cls._jobs_[func.__name__] = {'fn': func, 'frequency': frequency}

            return func
        return wrapper

    @classmethod
    def remove(cls, name):
        if name not in cls._jobs_:
            return
        del cls._jobs_[name]

if __name__ == '__main__':
    @Sisyphus.register(1)
    def echo():
        print('echo ...')
        time.sleep(3)

    @Sisyphus.register(2)
    def echo2():
        print('echo 2')
        time.sleep(1)
        sys.exit(0)

    sisyphus = Sisyphus()
    sisyphus()
