# Generic MQTT message Transcription Engine

import time
import logging
import typing
import traceback
import threading

# Scheduled callback happens every 0.5 seconds
SCHED_INTERVAL=0.5

class MQTEContext:
    def __init__(self, unix_ts, t_name, matched, state, logger):
        self.UNIXTS = unix_ts
        self.TNAME = t_name
        # The subscription topic that got matched
        # None if it is a scheduled callback
        self.MATCHED = matched
        self.STATE = state
        self.LOGGER = logger

class MQTEPayload:
    def __init__(self, topic, message, qos=2, retain=False):
        self.TOPIC = topic
        self.MESSAGE = message
        self.QOS = qos
        self.RETAIN = retain

class MQTEResult:
    def __init__(self, payload=None, need_sched=False):
        # Populate if the express want to publish a message
        self.PAYLOAD = payload
        # Set to `True` if the expression want a scheduled callback
        self.NEED_SCHED = need_sched

# Transcription callback interface
# - `context`: always populated by the MQTranscriber;
# - `payload`: present if not called from scheduled callback;
def MQTECallback(context :MQTEContext, payload :typing.Optional[MQTEPayload]) -> MQTEResult :
    return MQTEResult()

# Topic handling utilities
def CategorizeTopic(t):
    # Do not support '+' wildcard
    if '+' in t:
        return -2

    hash_cnt = t.count('#')
    # Invalid use of '#'
    if hash_cnt > 1:
        return -1
    if hash_cnt == 1 and not t.endswith('#'):
        return -1

    # 0 = literal; 1 = prefix
    return hash_cnt

def MatchTopic(topic, t_pfx):
    return topic.startswith(t_pfx)

def FindTopic(topic, t_pfxes):
    for t in t_pfxes:
        if MatchTopic(topic, t):
            return t
    return None

def InsertTopicPfx(t_pfx, pfx_set):
    r_pfxes = []
    for e_pfx in list(pfx_set):
        if MatchTopic(e_pfx, t_pfx):
            pfx_set.remove(e_pfx)
            r_pfxes.append(e_pfx)
    pfx_set.add(t_pfx)
    return r_pfxes

class MQTE:
    _SCHED = {'timer':None, 'lock':threading.Lock()}
    # Function ref to publish messages
    _PUBLISH = None

    def __init__(self, name, sub_topics, expr):
        self._NAME = name
        self._LOGGER = logging.getLogger("MQTE:"+name)
        self._EXPR = expr

        self._T_LIT = set()
        self._T_PFX = set()
        for t in sub_topics:
            tc = CategorizeTopic(t)
            if tc == 0:
                if t in self._T_LIT:
                    self._LOGGER.warning("Duplicate topic '%s'", t)
                else:
                    self._T_LIT.add(t)
            elif tc == 1:
                t_pfx = t[:-1]
                e_pfx = FindTopic(t_pfx, self._T_PFX)
                if e_pfx:
                    self._LOGGER.warning("Topic '%s#' covers '%s#'", e_pfx, t_pfx)
                else:
                    r_pfxes = InsertTopicPfx(t_pfx,self._T_PFX)
                    if r_pfxes:
                        self._LOGGER.warning("Topic '%s#' covers '%s#'", t_pfx,
                                             "#','".join(r_pfxes))
            else:
                raise Exception("Invalid/unsupported topic '%s'"%t)
        for t in list(self._T_LIT):
            e_pfx = FindTopic(t, self._T_PFX)
            if e_pfx:
                self._LOGGER.warning("Topic '%s#' covers '%s'", e_pfx, t)
                self._T_LIT.remove(t)
        self._LOGGER.info("Subscribing to %d literal and %d prefix topics",
                          len(self._T_LIT), len(self._T_PFX))

    def name(self):
        return self._NAME

    def sub_topics(self):
        return (list(self._T_LIT), list(self._T_PFX))

    def set_publish(self, func):
        self._PUBLISH = func

    def on_sched(self):
        self._SCHED['lock'].acquire()
        self._LOGGER.debug("Scheduled callback start");
        try:
            while self._CONNECTED:
                result = self._EXPR(MQTEContext(time.time(), self._NAME, None,
                                                self._STATE, self._LOGGER),
                                    None)
                self._PUBLISH(result.PAYLOAD)
                if not result.NEED_SCHED:
                   break
                self._SCHED['lock'].release()
                time.sleep(SCHED_INTERVAL)
                self._SCHED['lock'].acquire()
        except:
            self._LOGGER.error("Expression scheduled callback failed: %s",
                               traceback.format_exc());

        self._LOGGER.debug("Scheduled callback finish");
        self._SCHED['timer'] = None
        self._SCHED['lock'].release()

    def on_connected(self, unix_ts, con_count):
        with self._SCHED['lock']:
            self._CONNECTED = True
            self._STATE = {}

    def on_disconnected(self, unix_ts, final):
        with self._SCHED['lock']:
            self._CONNECTED = False

    def _match_topic(self, topic):
        if topic in self._T_LIT:
            return topic
        e_pfx = FindTopic(topic, self._T_PFX)
        return None if e_pfx is None else e_pfx+'#'

    def on_receive(self, unix_ts, topic, message, qos, retain):
        matched = self._match_topic(topic)
        if not matched:
            return False
        with self._SCHED['lock']:
            result = self._EXPR(MQTEContext(unix_ts, self._NAME, matched,
                                            self._STATE, self._LOGGER),
                                MQTEPayload(topic, message, qos, retain))
            self._PUBLISH(result.PAYLOAD)
            if result.NEED_SCHED and self._SCHED['timer'] is None:
                timer = threading.Timer(SCHED_INTERVAL, self.on_sched)
                self._SCHED['timer'] = timer
                timer.start()
        return True

