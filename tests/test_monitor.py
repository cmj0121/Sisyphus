#! /usr/bin/env python
#! coding: utf-8
# Copyright (C) 2017-2018 jaypan<sfffaaa@gmail.com>. All right reserved.

import pytest # pylint: disable=unused-import
import time
from sisyphus.sisyphus import Sisyphus
from multiprocessing import Process


def check_monitor_task(executed_jobs, check_data):
    executed_name = [_.split()[0] for _ in executed_jobs]
    assert executed_name == check_data, f'{executed_jobs} and {check_data} should be the same'

def test_monitor_task():

    @Sisyphus.register(0, 1)
    def my_sleep_01(): # pylint: disable=unused-variable
        time.sleep(5)

    @Sisyphus.register(0, 1)
    def my_sleep_02(): # pylint: disable=unused-variable
        time.sleep(10)

    sisyphus = Sisyphus()
    p = Process(target=sisyphus, args=())
    p.start()
    time.sleep(2)

    check_monitor_task(sisyphus.get_executes_jobs,
                       ['my_sleep_01', 'my_sleep_02'])
    time.sleep(7)
    check_monitor_task(sisyphus.get_executes_jobs,
                       ['my_sleep_02'])
    p.join()
