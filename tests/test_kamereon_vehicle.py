"""Vehicle data fetches: tyre pressure, charge mode, location heading."""
from unittest.mock import patch

from custom_components.nissan_connect.kamereon import NCISession, Feature, Tyre


BFF_BASE_URL = "https://nci-bff-web-prod.apps.eu2.kamereon.io/bff-web/"
USER_URL = (
    "https://alliance-platform-usersadapter-prod.apps.eu2.kamereon.io/"
    "user-adapter/v1/users/current"
)
CAR_ADAPTER_URL = (
    "https://alliance-platform-caradapter-prod.apps.eu2.kamereon.io/car-adapter/"
)


def make_vehicle(requests_mock, services=()):
    requests_mock.get(USER_URL, json={"userId": "test-user"})
    requests_mock.get(
        f"{BFF_BASE_URL}v5/users/test-user/cars",
        json={"data": [{
            "vin": "test-vin",
            "services": [
                {"id": service.value, "activationState": "ACTIVATED"}
                for service in services
            ],
        }]},
    )
    session = NCISession(region="EU")
    session._install_kamereon_token({
        "access_token": "kamereon-access-token",
        "token_type": "Bearer",
        "expires_in": 1800,
    })
    return session.fetch_vehicles()[0]


def car_url(endpoint):
    return f"{CAR_ADAPTER_URL}v1/cars/TEST-VIN/{endpoint}"


def test_fetch_pressure_parses_all_tyres(requests_mock):
    vehicle = make_vehicle(requests_mock)
    requests_mock.get(car_url("pressure"), json={"data": {"attributes": {
        "flPressure": 2223, "frPressure": 2258,
        "rlPressure": 2230, "rrPressure": 2378,
        "flStatus": 0, "frStatus": 0, "rlStatus": 0, "rrStatus": 1,
    }}})

    vehicle.fetch_pressure()

    assert vehicle.tyre_pressure == {
        Tyre.FRONT_LEFT: 2223,
        Tyre.FRONT_RIGHT: 2258,
        Tyre.REAR_LEFT: 2230,
        Tyre.REAR_RIGHT: 2378,
    }
    assert vehicle.tyre_status == {
        Tyre.FRONT_LEFT: 0,
        Tyre.FRONT_RIGHT: 0,
        Tyre.REAR_LEFT: 0,
        Tyre.REAR_RIGHT: 1,
    }


def test_fetch_pressure_unsupported_car_is_tolerated_and_not_retried(requests_mock):
    """A car without tyre sensors must not break fetch_all, nor be re-polled."""
    vehicle = make_vehicle(requests_mock)
    pressure = requests_mock.get(car_url("pressure"), status_code=403, json={
        "errors": [{"status": "Forbidden", "code": "403",
                    "detail": "Access is denied for this resource"}]
    })

    vehicle.fetch_pressure()
    vehicle.fetch_pressure()

    assert vehicle.tyre_pressure == {}
    assert vehicle.tyre_status == {}
    assert pressure.call_count == 1


def test_fetch_charge_mode_parses_mode(requests_mock):
    vehicle = make_vehicle(requests_mock, services=[Feature.BATTERY_STATUS])
    requests_mock.get(car_url("charge-mode"), json={"data": {"attributes": {
        "chargeMode": "always",
    }}})

    vehicle.fetch_charge_mode()

    assert vehicle.charge_mode == "always"


def test_fetch_charge_mode_skipped_without_battery_feature(requests_mock):
    vehicle = make_vehicle(requests_mock)
    charge_mode = requests_mock.get(car_url("charge-mode"), json={})

    vehicle.fetch_charge_mode()

    assert vehicle.charge_mode is None
    assert charge_mode.call_count == 0


def test_fetch_charge_mode_unsupported_car_is_tolerated_and_not_retried(requests_mock):
    vehicle = make_vehicle(requests_mock, services=[Feature.BATTERY_STATUS])
    charge_mode = requests_mock.get(car_url("charge-mode"), status_code=501, json={
        "errors": [{"status": "Not Implemented", "code": "501"}]
    })

    vehicle.fetch_charge_mode()
    vehicle.fetch_charge_mode()

    assert vehicle.charge_mode is None
    assert charge_mode.call_count == 1


def test_fetch_location_parses_heading(requests_mock):
    vehicle = make_vehicle(requests_mock, services=[Feature.MY_CAR_FINDER])
    requests_mock.get(car_url("location"), json={"data": {"attributes": {
        "gpsDirection": 288.0,
        "gpsLatitude": 59.9,
        "gpsLongitude": 10.8,
        "lastUpdateTime": "2026-09-02T06:36:27Z",
    }}})

    vehicle.fetch_location()

    assert vehicle.location == (59.9, 10.8)
    assert vehicle.location_direction == 288.0


def test_fetch_all_fetches_pressure_and_charge_mode(requests_mock):
    vehicle = make_vehicle(requests_mock)
    with patch.object(vehicle, "fetch_cockpit"), \
            patch.object(vehicle, "fetch_location"), \
            patch.object(vehicle, "fetch_battery_status"), \
            patch.object(vehicle, "fetch_hvac_status"), \
            patch.object(vehicle, "fetch_lock_status"), \
            patch.object(vehicle, "fetch_pressure") as fetch_pressure, \
            patch.object(vehicle, "fetch_charge_mode") as fetch_charge_mode:
        vehicle.fetch_all()

    assert fetch_pressure.call_count == 1
    assert fetch_charge_mode.call_count == 1
