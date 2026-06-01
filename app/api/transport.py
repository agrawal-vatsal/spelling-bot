"""Transport configuration.

The transport is the audio I/O layer between the browser and the pipeline. We
use SmallWebRTC (declared via the "webrtc" key), which the Pipecat runner serves
together with a prebuilt browser client — so there's no separate frontend to run.

Note on 1.x: voice-activity detection (VAD) and turn-taking are NOT configured
here anymore. In Pipecat 0.0.x they lived on TransportParams (vad_analyzer=...),
but in 1.x that field was removed — VAD now attaches to the user aggregator in
pipeline.py via LLMUserAggregatorParams. This file is therefore just audio
enablement; create_transport() consumes the dict below to build the transport
the runner selected.
"""

from pipecat.transports.base_transport import TransportParams


def get_transport_params() -> dict:
    """Return the per-transport params dict the runner uses to build transports.

    The value is a zero-arg factory (lambda) per transport type so the params
    are constructed lazily for whichever transport the client requests. We only
    support "webrtc" (SmallWebRTC).
    """
    return {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }