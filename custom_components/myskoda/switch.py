"""Switches for the MySkoda integration."""

import logging

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from myskoda.models.air_conditioning import AirConditioning
from myskoda.models.charging import (
    Charging,
    ChargingState,
    ChargingStatus,
    MaxChargeCurrent,
    Settings,
)
from myskoda.models.common import ActiveState, OnOffState
from myskoda.models.info import CapabilityId

from .const import COORDINATORS, DOMAIN
from .entity import MySkodaEntity
from .utils import InvalidCapabilityConfigurationError, add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[
            WindowHeating,
            EnableCharging,
            ReducedCurrent,
            BatteryCareMode,
        ],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaSwitch(MySkodaEntity, SwitchEntity):
    """Base class for all switches in the MySkoda integration."""

    pass


class WindowHeating(MySkodaSwitch):
    """Controls window heating."""

    entity_description = SwitchEntityDescription(
        key="window_heating",
        name="Window Heating",
        icon="mdi:car-defrost-front",
        device_class=SwitchDeviceClass.SWITCH,
    )

    def _air_conditioning(self) -> AirConditioning:
        air_conditioning = self.vehicle.air_conditioning
        if air_conditioning is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return air_conditioning

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        return (
            self._air_conditioning().window_heating_state.front == OnOffState.ON
            or self._air_conditioning().window_heating_state.rear == OnOffState.ON
        )

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self.coordinator.myskoda.stop_window_heating(self.vehicle.info.vin)
        _LOGGER.debug("Window heating disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.myskoda.start_window_heating(self.vehicle.info.vin)
        _LOGGER.debug("Window heating enabled.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.WINDOW_HEATING]


class ChargingSwitch(MySkodaSwitch):
    def _charging(self) -> Charging:
        charging = self.vehicle.charging
        if charging is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return charging

    def _settings(self) -> Settings:
        settings = self._charging().settings
        if settings is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )

        return settings

    def _status(self) -> ChargingStatus:
        status = self._charging().status
        if status is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


class BatteryCareMode(ChargingSwitch):
    """Controls battery care mode."""

    entity_description = SwitchEntityDescription(
        key="battery_care_mode",
        name="Battery Care Mode",
        icon="mdi:battery-heart-variant",
        device_class=SwitchDeviceClass.SWITCH,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        return self._settings().charging_care_mode == ActiveState.ACTIVATED

    async def async_turn_off(self, **kwargs):  # noqa: D102 # noqa: D102
        await self.coordinator.myskoda.set_battery_care_mode(
            self.vehicle.info.vin, False
        )
        _LOGGER.info("Battery care mode disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.myskoda.set_battery_care_mode(
            self.vehicle.info.vin, True
        )
        _LOGGER.info("Battery care mode enabled.")


class ReducedCurrent(ChargingSwitch):
    """Control whether to charge with reduced current."""

    entity_description = SwitchEntityDescription(
        key="reduced_current",
        name="Reduced Current",
        icon="mdi:current-ac",
        device_class=SwitchDeviceClass.SWITCH,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        return self._settings().max_charge_current_ac == MaxChargeCurrent.REDUCED

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self.coordinator.myskoda.set_reduced_current_limit(
            self.vehicle.info.vin, False
        )
        _LOGGER.info("Reduced current limit disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.myskoda.set_reduced_current_limit(
            self.vehicle.info.vin, True
        )
        _LOGGER.info("Reduced current limit enabled.")


class EnableCharging(ChargingSwitch):
    """Control whether the vehicle should be charging."""

    entity_description = SwitchEntityDescription(
        key="charging",
        name="Charging",
        icon="mdi:power-plug-battery",
        device_class=SwitchDeviceClass.SWITCH,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        return self._status().state == ChargingState.CHARGING

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self.coordinator.myskoda.stop_charging(self.vehicle.info.vin)
        _LOGGER.info("Charging stopped.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.myskoda.start_charging(self.vehicle.info.vin)
        _LOGGER.info("Charging started.")
