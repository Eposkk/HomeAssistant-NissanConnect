import pytest
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from custom_components.nissan_connect.kamereon import ChargingStatus, PluggedStatus, LockStatus, Door

from custom_components.nissan_connect.binary_sensor import (
    ChargingStatusEntity,
    PluggedStatusEntity,
    LockStatusEntity,
    DoorStatusEntity,
)

@pytest.fixture
def vehicle():
    class Vehicle:
        def __init__(self):
            self.charging = None
            self.charging_speed = None
            self.battery_status_last_updated = None
            self.plugged_in = None
            self.plugged_in_time = None
            self.unplugged_time = None
            self.lock_status = None
            self.door_status = {}

    return Vehicle()

@pytest.fixture
def coordinator(hass):
    async def async_update_data():
        return {}

    return DataUpdateCoordinator(hass, None, name="test", update_method=async_update_data)

async def test_charging_status_entity(vehicle, coordinator):
    entity = ChargingStatusEntity(coordinator, vehicle)
    assert entity.is_on == STATE_UNKNOWN

    vehicle.charging = ChargingStatus.CHARGING
    assert entity.is_on is True

    vehicle.charging = ChargingStatus.NOT_CHARGING
    assert entity.is_on is False

async def test_plugged_status_entity(vehicle, coordinator):
    entity = PluggedStatusEntity(coordinator, vehicle)
    assert entity.is_on == STATE_UNKNOWN

    vehicle.plugged_in = PluggedStatus.PLUGGED
    assert entity.is_on is True

    vehicle.plugged_in = PluggedStatus.NOT_PLUGGED
    assert entity.is_on is False

async def test_lock_status_entity(vehicle, coordinator):
    entity = LockStatusEntity(coordinator, vehicle)
    assert entity.is_on is False

    vehicle.lock_status = LockStatus.LOCKED
    assert entity.is_on is False

    vehicle.lock_status = LockStatus.UNLOCKED
    assert entity.is_on is True

async def test_door_status_entity(vehicle, coordinator):
    entity = DoorStatusEntity(coordinator, vehicle, Door.FRONT_LEFT)
    assert entity.is_on == STATE_UNKNOWN

    vehicle.door_status = {Door.FRONT_LEFT: LockStatus.CLOSED}
    assert entity.is_on is False

    vehicle.door_status = {Door.FRONT_LEFT: LockStatus.OPEN}
    assert entity.is_on is True
