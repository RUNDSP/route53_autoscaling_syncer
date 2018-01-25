#!/usr/bin/env python

__version__ = '1.2.2'

import argparse
import datetime
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import logging
from SocketServer import ThreadingMixIn
from threading import Lock, Thread
import time

import boto
import boto.ec2
import boto.ec2.autoscale
import boto.route53
import boto.route53.record


logger = logging.getLogger(__name__)


last_success = None
last_success_lock = Lock()
max_seconds_healthy = 20


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


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


def start_health_check_server(host, port):
    logging.basicConfig()
    logging.error('starting server')
    server = ThreadedHTTPServer((host, port), HealthCheckHTTPRequestHandler)
    server.serve_forever()


def main(interval, region, group_name, zone, dns_name, ttl):
    global last_success
    logging.basicConfig()
    ec2_conn = boto.ec2.connect_to_region(region)
    as_conn = boto.ec2.autoscale.connect_to_region(region)
    r53_conn = boto.route53.connect_to_region(region)
    z = r53_conn.get_zone(zone)
    while True:
        try:
            group = as_conn.get_all_groups([group_name])[0]
            instances_ids = [i.instance_id for i in group.instances]
            reservations = ec2_conn.get_all_reservations(instances_ids)
            instances = [i for r in reservations for i in r.instances]
            ips = [i.private_ip_address for i in instances]
            logging.debug('ips: ' + repr(ips))
            if len(ips) > 0:
                c = boto.route53.record.ResourceRecordSets(r53_conn, z.id)
                change = c.add_change("UPSERT", dns_name, type="A", ttl=ttl)
                for ip in ips:
                    change.add_value(ip)
                c.commit()
                logging.debug('updated ips')
            last_success_lock.acquire()
            try:
                last_success = datetime.datetime.utcnow()
            finally:
                last_success_lock.release()
            time.sleep(interval)
        except Exception, ex:
            logger.error('Exception caught: ' + ex.message)
            continue


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interface', help='Interface to which to bind',
                        type=str, default='0.0.0.0')
    parser.add_argument('--port', help='Port to which to bind',
                        type=int, required=True)
    parser.add_argument('--region', help='AWS region',
                        type=str, required=True)
    parser.add_argument('--autoscaling-group', type=str, required=True)
    parser.add_argument('--interval', help='How frequently to run (s)',
                        type=int, required=True)
    parser.add_argument('--zone', type=str, required=True)
    parser.add_argument('--domain', type=str, required=True)
    parser.add_argument('--ttl', type=int, default=10)
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    t_main = Thread(target=main,
                    args=(args.interval, args.region, args.autoscaling_group,
                          args.zone, args.domain, args.ttl))
    t_main.daemon = True
    t_main.start()
    start_health_check_server(args.interface, args.port)
