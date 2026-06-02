"""Transport configuration for SmallWebRTC (audio only).

VAD attaches via LLMUserAggregatorParams in pipeline.py, not here.
"""

from pipecat.transports.base_transport import TransportParams


def get_transport_params() -> dict:
    """Return a transport-type → factory mapping for the Pipecat runner."""
    return {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }
