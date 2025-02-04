# MQTT Message Transcriber
Allows highly customized transcription of MQTT messages.

Not all MQTT data providers produce messages in formats that is easily
consumable by your IoT applications. This service enables you to subscribe
one or more source topics and produce transcribed messages to your target
topics.

Notably, it is possible to produce transcriptions asynchronously, e.g.
consume more than one messages over a certain period of time, storing the
intermediary states, and then produce a "summarized" message autonomously
(i.e. not needing input messages as triggers to produce output).

## Install
Recommended running with Python 3.7+.

1. Install dependent modules:
    ```
    python3 -m pip install -r requirements.txt
    ```
2. Configure the service:
    - Create `__deploy__` sub-directory;
    - Make a copy of `Config.py` in `__deploy__`;
    - Make a symbolic link to `MQTE.py` at `__deploy__/MQTE.py`
    - Edit `__deploy__/Config.py` (see the following section)
3. Test connecting to the MQTT server:
    ```
    DRYRUN=1 python3 MQTranscriber.py
    ```
4. Test publishing data:
    ```
    python3 MQTranscriber.py
    ```
5. Install as service:
    ```
    > crontab -e
    # m h dom mon dow   command
    * * * * *       cd /path/to/Transcriber/__deploy__ && flock -E 0 -xnF Service.lock python3 ../MQTranscriber.py
    ```

## Transcriber Programming
* All transcribers must be instances of `MQTE` class, which takes three
  parameters:
  1. `name` is an arbitrary string to differentiate multiple transcribers;
  2. `sub_topics` is a list of topics to subscribe -- they can be either
     literal strings, or a prefix pattern (e.g. "/path/to/topic/#").
     (Currently only '#' is accepted, '+' is not supported.)
  3. `expr` is for passing a callback function that handles the transcription.
     It must match the `MQTECallback()` interface.

* When a message is received from subscribed topic, your callback
  function is invoked with both `context` and `payload` parameters.

  Noteably:
   - `context.MATCHED` contains the exact subscription topic that got matched.
   - `context.STATE` is a non-ephemeral storage space to allow your code to
     pass information across multiple callback invocations.

  The return value must be an `MQTEResult` instance.
  - For a 1:1 transcription, you only need to provide the transcribed message
    in the `payload` field, which will be published automatically;
  - However, if you need to collect multiple input message to produce a
    transcribed message:
    - Stage the incomplete information in `context.STATE`, and return without
      `payload`. The saved states will be presented to your callback function
      when a future message arrives.
    - When you finally collected sufficient info, craft the transcribed
      message and clear `context.STATE`, then return with `payload` set.
  - In an even trickier situation, where the information you need are not only
    broken into several message, but also you may or may not receive a certain
    part, and you must factor time into the transcription.
    - Again stage the incomplete information in `context.STATE`, but when you
      return (without `payload`), set `need_sched=True`;
    - This will trigger periodic (currently every ~0.5s), non-message-driven
      calls to your callback function, which can be differentiated from the
      message-driven calls by `context.MATCHED=None` and `payload=None`.
      - The `need_sched` return value from non-message-driven call determines
        whether the call will continue to be fired or stopped;
    - Message-driven calls will continue be dispatched as messages arrive
      on the subscribed topics, and both non-message-driven and message-driven
      calls will share the same `context.STATE`. (The framework ensures safe
      concurrent accesses.)
    - In non-message-driven calls, you can monitor `context.STATE` as well as
      track the duration of your wait. When conditions are met, e.g. all the
      needed data are collected, or wait time expired, return with `payload`
      set to trigger publishing.
      - Note that you could publish multiple messages in this way by keeping
        `need_sched=True`, and track the publish progress in `context.STATE`.