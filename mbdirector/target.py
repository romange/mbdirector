# Copyright (C) 2019 Redis Labs Ltd.
#
# This file is part of mbdirector.
#
# mbdirector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2.
#
# mbdirector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with memtier_benchmark.  If not, see <http://www.gnu.org/licenses/>.

"""
Setup and tear down test targets.
"""

import os.path
import subprocess
import time
import logging

import redis


class Target(object):
    """
    Currently hard coded to RedisProcessTarget, but should be extended in
    the future to provision RE databases, etc.
    """

    @classmethod
    def from_json(cls, config, json):
        """
        Create a specific subclass from a generic json spec.
        """
        return RedisProcessTarget(config, **json)


class RedisProcessTarget(object):
    """
    Implements a local Redis process target.
    """

    def __init__(self, config, **kwargs):
        self.binary = kwargs.get('binary', None)
        if self.binary:
            self.args = [self.binary] + list(kwargs['args'])
        else:
            self.args = []
        self.config = config
        self.skip_ping = kwargs.get('skip_ping_on_setup', False)
        self.auto_port_bind_args = kwargs.get('auto_port_bind_args', True)
        self.name = kwargs['name']
        self.process = None
        self._conn = None

        # Configure Redis
        if self.auto_port_bind_args:
            self.args += ['--port', str(config.redis_process_port),
                          '--bind', '127.0.0.1']
        self.args += ['--logfile', os.path.join(config.results_dir,
                                                'redis.log')]

    def setup(self):
        logging.debug('  Command: %s', ' '.join(self.args))
        if self.binary:
            self.process = subprocess.Popen(
                stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                executable=self.binary, args=self.args)
        if self.skip_ping:
            time.sleep(1)
        else:
            self._ping()

    def teardown(self):
        if self.process is not None:
            self.process.terminate()
            self.process.wait()
            self.process = None

    def get_redis_url(self):
        return 'redis://127.0.0.1:6379'

    def __del__(self):
        self.teardown()

    def _get_conn(self, retries=10, interval=0.1):
        if self._conn:
            return self._conn

        while retries:
            try:
                self._conn = redis.from_url(self.get_redis_url())
                self._conn.ping()
                return self._conn
            except redis.ConnectionError:
                retries -= 1
                if retries:
                    time.sleep(interval)
                else:
                    raise

    def _ping(self, retries=20, interval=0.2):
        while retries:
            try:
                return self._get_conn().ping()
            except redis.RedisError:
                retries -= 1
                if not retries:
                    raise
                time.sleep(interval)
