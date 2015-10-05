#!/usr/bin/env python

__version__ = '0.1'

import datetime
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import logging
from threading import Lock, Thread
import time


logger = logging.getLogger(__name__)


last_success = None
last_success_lock = Lock()
max_seconds_healthy = 30


class HealthCheckHTTPRequestHandler(BaseHTTPRequestHandler):

    server_version = "Route53AutoscalingSyncerHealthCheck/" + __version__

    def do_GET(self):
        return self.do_HEAD()

    def do_HEAD(self):
        try:
            last_success_lock.acquire()
            try:
                tdiff = (datetime.datetime.utcnow() - last_success) \
                    .total_seconds()
            finally:
                last_success_lock.release()
            if tdiff <= max_seconds_healthy:
                self.send_response(200)
            else:
                logger.error('unhealthy, responding 500, tdiff %s', tdiff)
                self.send_response(500)
        except Exception, e:
            logger.error('unhealthy, exception, %s',
                         getattr(e, 'message', ''))
            self.send_response(500)
        finally:
            self.end_headers()
        return None


def start_health_check_server():
    logging.basicConfig()
    logging.error('starting server')
    server = HTTPServer(('0.0.0.0', 80), HealthCheckHTTPRequestHandler)
    server.serve_forever()


def main(interval):
    global last_success
    logging.basicConfig()
    while True:
        # TODO
        logging.error('doing it')
        last_success_lock.acquire()
        try:
            last_success = datetime.datetime.utcnow()
        finally:
            last_success_lock.release()
        time.sleep(interval)


if __name__ == '__main__':
    t_main = Thread(target=main, args=(5,))
    t_main.daemon = True
    t_main.start()
    start_health_check_server()
