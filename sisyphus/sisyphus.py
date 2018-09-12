#! /usr/bin/env python
# Copyright (C) 2018-2018 cmj<cmj@cmj.tw>. All right reserved.

import time
import logging
from multiprocessing import Process, Value
import os

try:
    from setproctitle import setproctitle as procname # pylint: disable=import-error
except ImportError:
    try:
        from procname import setprocname as procname
    except ImportError:
        procname = lambda x: None


class Sisyphus(object):
    _jobs_ = {}

    # NOTE - default configuration
    config = {
        'SISYPHUS_RPC': f'ipc://{os.path.expanduser("~")}/.sisyphus.sock',
        'ITERATOR_SECONDES': 5,
    }


    def __init__(self, debug=False):
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

    def __call__(self, frequency=None):
        try:
            while self._jobs_:
                for name, name_conf in self._jobs_.items():
                    if 'proc' not in name_conf or not name_conf['proc'].is_alive():
                        if not name_conf['counter'].value:
                            self.warning(f'Terminate job {name} since counter=0')
                            del self._jobs_[name]
                            break
                        elif 'proc' in name_conf:
                            del self._jobs_[name]['proc']

                        self._jobs_[name]['proc'] = Process(target=self.worker, args=(name, ))
                        self._jobs_[name]['proc'].start()
                        self.warning(f'new job `{name}` on PID#{self._jobs_[name]["proc"].pid}')
                time.sleep(frequency or self.config['ITERATOR_SECONDES'])
        except KeyboardInterrupt:
            for _, conf in self._jobs_.items():
                _ = conf['proc'].kill() if hasattr(conf['proc'], 'kill') else conf['proc'].terminate()
            self.critical(f'Ctrl-C')

    def worker(self, name):
        procname(f'{name} ({self._jobs_[name]["frequency"]})')
        while self._jobs_[name]['counter'].value:
            if self._jobs_[name]['counter'].value > 0:
                # count-down the counter
                self._jobs_[name]['counter'].value -= 1

            self._jobs_[name]['fn'].__globals__['worker'] = self
            self._jobs_[name]['executed'].value = True
            try:
                self._jobs_[name]['fn']()
            finally:
                self._jobs_[name]['executed'].value = False
            time.sleep(self._jobs_[name]['frequency'])

    def load_config(self, filepath=None):
        self.info(f'Loading configuration {filepath} ...')
        raise NotImplementedError

    @property
    def get_executes_jobs(self):
        return [f'{job} ({item["fn"]})' for job, item in self._jobs_.items()
                if item['executed'].value]

    @property
    def jobs(self):
        jobs = [f'- {job} ({item["fn"]})' for job, item in self._jobs_.items()]
        return '\n'.join(jobs)

    @classmethod
    def register(cls, frequency=1, counter=0):
        def wrapper(func):
            if func.__name__ in cls._jobs_:
                raise KeyError(func.__name__)

            cls._jobs_[func.__name__] = {
                'fn': func,
                'frequency': frequency,
                'counter': Value('i', counter), # Global variable for the multi-processes
                'executed': Value('i', False)
            }

            return func
        return wrapper

if __name__ == '__main__':
    pass
