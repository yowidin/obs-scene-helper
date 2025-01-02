"""
Based on the obws_python/events.py implementation, with the main addition of
getting a notification once the thread has exited for any reason.
"""

import json
import logging
import threading

from websocket import WebSocketConnectionClosedException, WebSocketTimeoutException

from obsws_python.baseclient import ObsClient
from obsws_python.callback import Callback
from obsws_python.error import OBSSDKError, OBSSDKTimeoutError
from obsws_python.subs import Subs

from obs_scene_helper.controller.system.log import Log

"""
A class to interact with obs-websocket events
defined in official github repo
https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#events
"""

logger = logging.getLogger(__name__)


class EventClient:
    LOG_NAME = 'ec'

    def __init__(self, on_disconnected, **kwargs):
        self.logger = Log.child(self.LOG_NAME)
        defaultkwargs = {"subs": Subs.LOW_VOLUME}
        kwargs = defaultkwargs | kwargs
        self.base_client = ObsClient(**kwargs)
        self.worker = None
        self.on_disconnected = on_disconnected

        try:
            success = self.base_client.authenticate()
            self.logger.info(
                f"Successfully identified {self} with the server using RPC version:{success['negotiatedRpcVersion']}"
            )
        except OBSSDKError as e:
            self.logger.error(f"{type(e).__name__}: {e}")
            self._report_disconnect()
            raise

        self.callback = Callback()
        self.subscribe()

    def _report_disconnect(self):
        if self.on_disconnected:
            self.on_disconnected()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.disconnect()

    def __repr__(self):
        return type(
            self
        ).__name__ + "(host='{host}', port={port}, password='{password}', subs={subs}, timeout={timeout})".format(
            **self.base_client.__dict__,
        )

    def __str__(self):
        return type(self).__name__

    def subscribe(self):
        self.base_client.ws.settimeout(None)
        stop_event = threading.Event()
        self.worker = threading.Thread(
            target=self.trigger, daemon=True, args=(stop_event,)
        )
        self.worker.start()

    def trigger(self, stop_event):
        """
        Continuously listen for events.

        Triggers a callback on event received.
        """
        while not stop_event.is_set():
            try:
                if response := self.base_client.ws.recv():
                    event = json.loads(response)
                    self.logger.debug(f"Event received {event}")
                    type_, data = (
                        event["d"].get("eventType"),
                        event["d"].get("eventData"),
                    )
                    self.callback.trigger(type_, data if data else {})
            except WebSocketTimeoutException as e:
                self.logger.exception(f"{type(e).__name__}: {e}")
                raise OBSSDKTimeoutError("Timeout while waiting for event") from e
            except (WebSocketConnectionClosedException, OSError) as e:
                self.logger.debug(f"{type(e).__name__} terminating the event thread")
                stop_event.set()

        self._report_disconnect()

    def disconnect(self):
        """stop listening for events"""

        self.base_client.ws.close()
        self.worker.join()

    unsubscribe = disconnect
