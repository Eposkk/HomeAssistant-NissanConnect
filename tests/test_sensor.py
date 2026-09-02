import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfLength, UnitOfTime, UnitOfPressure
from custom_components.nissan_connect.base import KamereonEntity
from custom_components.nissan_connect.kamereon import ChargingSpeed, Feature, Tyre

from custom_components.nissan_connect.sensor import (
    BatteryLevelSensor,
    InternalTemperatureSensor,
    ExternalTemperatureSensor,
    RangeSensor,
    OdometerSensor,
    StatisticSensor,
    ChargeTimeRequiredSensor,
    TimestampSensor,
    ChargingSpeedSensor,
    TyrePressureSensor,
    ChargeModeSensor,
    async_setup_entry
)

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {
        'nissan_connect': {
            'test_account': {
                'vehicles': {
                    'test_vehicle': MagicMock(
                        battery_level=80,
                        internal_temperature=22.5,
                        external_temperature=15.0,
                        range_hvac_on=100,
                        range_hvac_off=120,
                        total_mileage=5000,
                        charge_time_required_to_full={ChargingSpeed.NORMAL: 60, ChargingSpeed.FAST: 30, ChargingSpeed.ADAPTIVE: None},
                        tyre_pressure={Tyre.FRONT_LEFT: 2223, Tyre.FRONT_RIGHT: 2258, Tyre.REAR_LEFT: 2230, Tyre.REAR_RIGHT: 2378},
                        tyre_status={Tyre.FRONT_LEFT: 0, Tyre.FRONT_RIGHT: 0, Tyre.REAR_LEFT: 0, Tyre.REAR_RIGHT: 0},
                        charge_mode='always',
                        features=[Feature.BATTERY_STATUS, Feature.DRIVING_JOURNEY_HISTORY]
                    )
                },
                'coordinator_fetch': AsyncMock(),
                'coordinator_statistics': AsyncMock()
            }
        }
    }
    return hass

@pytest.fixture
def mock_config():
    return MagicMock(data={'email': 'test_account', 'imperial_distance': False})

@pytest.fixture
def mock_async_add_entities():
    return AsyncMock()

@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config, mock_async_add_entities):
    await async_setup_entry(mock_hass, mock_config, mock_async_add_entities)
    assert mock_async_add_entities.call_count == 1
    entities = mock_async_add_entities.call_args[0][0]
    assert len(entities) > 0
    assert any(isinstance(e, ChargingSpeedSensor) for e in entities)
    assert sum(isinstance(e, TyrePressureSensor) for e in entities) == 4
    assert sum(isinstance(e, ChargeModeSensor) for e in entities) == 1

@pytest.mark.asyncio
async def test_async_setup_entry_skips_unsupported_optional_sensors(mock_hass, mock_config, mock_async_add_entities):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    vehicle.tyre_pressure = {}
    vehicle.charge_mode = None
    await async_setup_entry(mock_hass, mock_config, mock_async_add_entities)
    entities = mock_async_add_entities.call_args[0][0]
    assert not any(isinstance(e, TyrePressureSensor) for e in entities)
    assert not any(isinstance(e, ChargeModeSensor) for e in entities)

def test_battery_level_sensor(mock_hass):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    sensor = BatteryLevelSensor(coordinator, vehicle)
    assert sensor.state == 80

def test_internal_temperature_sensor(mock_hass):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    sensor = InternalTemperatureSensor(coordinator, vehicle)
    assert sensor.native_value == 22.5

def test_external_temperature_sensor(mock_hass):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    sensor = ExternalTemperatureSensor(coordinator, vehicle)
    assert sensor.native_value == 15.0

def test_range_sensor(mock_hass):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    sensor = RangeSensor(coordinator, vehicle, True, False)
    assert sensor.native_value == 100

def test_odometer_sensor(mock_hass):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    sensor = OdometerSensor(coordinator, vehicle, False)
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    assert sensor.native_value == 5000

def test_charge_time_required_sensor(mock_hass):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    sensor = ChargeTimeRequiredSensor(coordinator, vehicle, ChargingSpeed.NORMAL)
    assert sensor.native_value == 60

def test_timestamp_sensor(mock_hass):
    vehicle = mock_hass.data['nissan_connect']['test_account']['vehicles']['test_vehicle']
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    sensor = TimestampSensor(coordinator, vehicle, 'battery_status_last_updated', 'last_updated', 'mdi:clock-time-eleven-outline')

def test_charging_speed_sensor(mock_hass):
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    vehicle = MagicMock(charging_speed=ChargingSpeed.FAST)
    sensor = ChargingSpeedSensor(coordinator, vehicle)
    assert sensor.native_value == 'fast'

    vehicle.charging_speed = ChargingSpeed.NONE
    assert sensor.native_value == 'none'

    vehicle.charging_speed = None
    assert sensor.native_value is None

def test_tyre_pressure_sensor(mock_hass):
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    vehicle = MagicMock(tyre_pressure={Tyre.REAR_RIGHT: 2378}, tyre_status={Tyre.REAR_RIGHT: 1})
    sensor = TyrePressureSensor(coordinator, vehicle, Tyre.REAR_RIGHT)
    assert sensor.native_value == 2378
    assert sensor.native_unit_of_measurement == UnitOfPressure.MBAR
    assert sensor.extra_state_attributes == {'status': 1}
    assert sensor._attr_translation_key == 'tyre_pressure_rear_right'

def test_tyre_pressure_sensor_missing_tyre_is_unknown(mock_hass):
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    vehicle = MagicMock(tyre_pressure={}, tyre_status={})
    sensor = TyrePressureSensor(coordinator, vehicle, Tyre.FRONT_LEFT)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {'status': None}

def test_charge_mode_sensor_maps_kamereon_values(mock_hass):
    coordinator = mock_hass.data['nissan_connect']['test_account']['coordinator_fetch']
    vehicle = MagicMock(charge_mode='always')
    sensor = ChargeModeSensor(coordinator, vehicle)
    assert sensor.native_value == 'always'

    vehicle.charge_mode = 'always_charging'
    assert sensor.native_value == 'always'

    vehicle.charge_mode = 'schedule_mode'
    assert sensor.native_value == 'scheduled'

    vehicle.charge_mode = 'scheduled'
    assert sensor.native_value == 'scheduled'

    vehicle.charge_mode = 'something_new'
    assert sensor.native_value is None

    vehicle.charge_mode = None
    assert sensor.native_value is None
