import pytest
from _agent_coordination.tools.event_bus import EventBus


def test_publish_subscribe():
    bus = EventBus()
    received = []
    def callback(msg):
        received.append(msg)
        return False

    bus.subscribe('TEST_TOPIC', callback)
    result = bus.publish('TEST_TOPIC', {'foo': 'bar'})
    assert result is True
    assert len(received) == 1
    assert received[0]['type'] == 'TEST_TOPIC'
    assert received[0]['payload'] == {'foo': 'bar'}


def test_acknowledgment_success():
    bus = EventBus()
    acked = []
    def callback_ack(msg):
        acked.append(msg['id'])
        return True

    bus.subscribe('ACK_TOPIC', callback_ack)
    result = bus.publish('ACK_TOPIC', {'key': 'value'}, ack_required=True, timeout=1.0)
    assert result is True
    assert len(acked) == 1


def test_acknowledgment_timeout():
    bus = EventBus()
    def callback_no_ack(msg):
        return False

    bus.subscribe('TIMEOUT_TOPIC', callback_no_ack)
    result = bus.publish('TIMEOUT_TOPIC', {'a': 1}, ack_required=True, timeout=0.5)
    assert result is False 
