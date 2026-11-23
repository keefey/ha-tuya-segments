"""Encoder checked against values captured from a real ALP235HA chain."""

import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location(
    "packet",
    pathlib.Path(__file__).parents[1] / "custom_components/tuya_segments/packet.py",
)
packet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packet)


def test_captured_app_values():
    # From the Smart Life app: segment 1 red, segment 10 blue, segments 2 and 3 green
    assert packet.encode([0], 360, 91, 65) == ["AQIBAWhbQQAAgQAA"]
    assert packet.encode([9], 243, 91, 65) == ["AQIBAPNbQQAAgQAJ"]
    assert packet.encode([1], 134, 100, 65) == ["AQIBAIZkQQAAgQAB"]
    assert packet.encode([2], 134, 100, 65) == ["AQIBAIZkQQAAgQAC"]


def test_hardware_verified_writes():
    # Written from HA and visually confirmed on the chain
    assert packet.encode([4], 360, 91, 65) == ["AQIBAWhbQQAAgQAE"]
    assert packet.encode([0, 1, 2], 240, 91, 65) == ["AQIBAPBbQQAAgwAAAAEAAg=="]


def test_chunking():
    pkts = packet.encode(list(range(200)), 0, 0, 50)
    assert len(pkts) == 2
