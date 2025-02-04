# Generic MQTT message transcriber

import os
import logging
import signal
import json

import MQTE

from common import MQPubCli

from __deploy__ import Config

DEBUG = os.environ.get('DEBUG')
logging.basicConfig(level=logging.NOTSET if DEBUG else logging.WARNING)

DRYRUN = os.environ.get('DRYRUN')

def MergePfxes(src, dst):
    for t in src:
        if MQTE.FindTopic(t, dst):
            continue
        MQTE.InsertTopicPfx(t, dst)

class MQTranscriber(MQPubCli.IntervalPublisher):

    def __init__(self, name, topic_pfx, dryrun, *,
                 dryrun_loglevel = logging.WARNING,
                 tlist):
        self._TLIST = tlist
        early_logger = logging.getLogger(name)

        lits = set()
        pfxes = set()
        for t in tlist:
            early_logger.debug("Initializing transcriber '%s'...", t.name())
            t.set_publish(lambda payload, o=self: o._T_Publish(payload))

            t_lits, t_pfxes = t.sub_topics()
            lits.update(t_lits)     
            MergePfxes(t_pfxes, pfxes)
        for lit in list(lits):
            if MQTE.FindTopic(lit, pfxes):
                lits.remove(lit)
        early_logger.info("%d transcribers with %d literal and %d prefix topics",
                          len(self._TLIST), len(lits), len(pfxes))

        sub_pairs = [(lit, 2) for lit in lits]
        sub_pairs+= [(pfx+'#', 2) for pfx in pfxes]
        super().__init__(name, topic_pfx, dryrun,
                         dryrun_loglevel = dryrun_loglevel,
                         sub_pairs=sub_pairs)

    def _T_Publish(self, payload):
        if payload:
            self._publish(payload.TOPIC, payload.MESSAGE, payload.QOS, payload.RETAIN)

    def on_connected(self, unix_ts, con_count):
        for t in self._TLIST:
            t.on_connected(unix_ts, con_count)

    def on_disconnected(self, unix_ts, final):
        for t in self._TLIST:
            t.on_disconnected(unix_ts, final)

    def on_receive(self, unix_ts, topic, message, qos, retain):
        match_cnt = 0
        for t in self._TLIST:
            if t.on_receive(unix_ts, topic, message, qos, retain):
                match_cnt+= 1

        if match_cnt:
            self._LOGGER.info("Message processed by %d transcribers", match_cnt)
        else:
            self._LOGGER.warning("Message for topic '%s' without transcriber", topic)

service = MQTranscriber(__name__, Config.TOPIC_PFX, DRYRUN,
                        tlist=Config.TLIST)

# Handle keyboard interruption
def CtrlCHandler(sig, frame):
    service.stop()
signal.signal(signal.SIGINT, CtrlCHandler)

service.run(Config.SERVER, Config.PORT, Config.USER, Config.PASS,
            Config.CACERTS, 60)
