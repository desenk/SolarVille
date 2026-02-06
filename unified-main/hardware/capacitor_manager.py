# Branch: unified-main
# File: capacitor_manager.py

"""Capacitor/battery storage manager for SolarVille system."""

import logging
import random

class CapacitorManager:
    """Manages supercapacitor or battery storage for prosumers."""

    def __init__(self, mock_mode: bool = True):
        """
        Initialize capacitor manager.

        Args:
            mock_mode: If True, simulate storage without hardware
        """
        self.mock_mode = mock_mode
        self.logger = logging.getLogger(__name__)

        # Storage state
        self.capacity = 1.0  # kWh total capacity (mock)
        self.soc = 0.5  # State of charge (0-1), start at 50%
        self.min_soc = 0.2  # Don't discharge below 20%
        self.max_soc = 1.0  # Don't charge above 100%

        self._initialize_capacitors()

    def _initialize_capacitors(self):
        """Initialize storage hardware or mock."""
        if self.mock_mode:
            self.logger.info(f"Capacitor initialized in mock mode (capacity: {self.capacity} kWh, SOC: {self.soc*100:.0f}%)")
        else:
            # TODO: Initialize real storage hardware
            self.logger.info("Capacitor hardware initialization not implemented")

    def charge(self, energy: float) -> float:
        """
        Charge the capacitor with available energy.

        Args:
            energy: Energy available for charging (kWh)

        Returns:
            Energy actually stored (kWh)
        """
        available_capacity = (self.max_soc - self.soc) * self.capacity
        energy_stored = min(energy, available_capacity)
        self.soc += energy_stored / self.capacity

        if energy_stored > 0:
            self.logger.debug(f"Charged {energy_stored:.3f} kWh, SOC now {self.soc*100:.1f}%")

        return energy_stored

    def discharge(self, energy: float) -> float:
        """
        Discharge energy from the capacitor.

        Args:
            energy: Energy requested (kWh)

        Returns:
            Energy actually provided (kWh)
        """
        available_energy = (self.soc - self.min_soc) * self.capacity
        energy_provided = min(energy, available_energy)
        self.soc -= energy_provided / self.capacity

        if energy_provided > 0:
            self.logger.debug(f"Discharged {energy_provided:.3f} kWh, SOC now {self.soc*100:.1f}%")

        return energy_provided

    def get_soc(self) -> float:
        """Get current state of charge (0-1)."""
        return self.soc

    def get_available_energy(self) -> float:
        """Get energy available for discharge (kWh)."""
        return (self.soc - self.min_soc) * self.capacity

    def get_available_capacity(self) -> float:
        """Get capacity available for charging (kWh)."""
        return (self.max_soc - self.soc) * self.capacity

    def cleanup(self):
        """Cleanup storage resources."""
        pass
