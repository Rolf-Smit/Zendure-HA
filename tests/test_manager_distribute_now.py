"""Changing the operation or manual power redistributes immediately, using the last P1 reading."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from custom_components.zendure_ha.const import ManagerMode
from custom_components.zendure_ha.manager import ZendureManager


def _make_manager_harness(p1_state: str | None = "350", *, online: bool = True) -> ZendureManager:
    manager = object.__new__(ZendureManager)
    states = {} if p1_state is None else {"sensor.p1": SimpleNamespace(state=p1_state)}
    manager.hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
    manager.p1meter = "sensor.p1"
    manager.p1meterEvent = lambda: None
    manager.p1_factor = 1
    manager.devices = [SimpleNamespace(online=online)]
    manager.operation = ManagerMode.OFF
    manager.distribute_lock = asyncio.Lock()
    manager.distributed = []

    async def _distribute(p1: int, isFast: bool, _time: Any) -> None:
        manager.distributed.append((p1, isFast))

    manager.distribute = _distribute
    return manager


async def test_operation_change_distributes_with_last_p1() -> None:
    manager = _make_manager_harness()
    await manager.update_operation(SimpleNamespace(value=ManagerMode.MANUAL.value), None)
    assert manager.distributed == [(350, True)]


async def test_operation_off_does_not_distribute() -> None:
    manager = _make_manager_harness()
    manager.devices[0].power_off = lambda: asyncio.sleep(0)
    await manager.update_operation(SimpleNamespace(value=ManagerMode.OFF.value), None)
    assert manager.distributed == []


async def test_manual_power_change_distributes_in_manual_mode() -> None:
    manager = _make_manager_harness()
    manager.operation = ManagerMode.MANUAL
    await manager.update_manualpower(None, -800)
    assert manager.distributed == [(350, True)]


async def test_manual_power_change_ignored_outside_manual_mode() -> None:
    manager = _make_manager_harness()
    manager.operation = ManagerMode.MATCHING
    await manager.update_manualpower(None, -800)
    assert manager.distributed == []


async def test_no_distribution_without_usable_p1_reading() -> None:
    for manager in (_make_manager_harness(None), _make_manager_harness("unavailable")):
        manager.operation = ManagerMode.MANUAL
        await manager.update_manualpower(None, 500)
        assert manager.distributed == []


async def test_no_distribution_when_all_devices_offline() -> None:
    manager = _make_manager_harness(online=False)
    manager.operation = ManagerMode.MANUAL
    await manager.update_manualpower(None, 500)
    assert manager.distributed == []
