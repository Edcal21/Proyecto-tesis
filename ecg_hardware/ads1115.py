"""
Lector reutilizable para ADS1115 en Raspberry Pi.

Provee una función `stream_samples` que genera dicts con:
  { 'timestamp': ISO8601Z, 'raw': int16, 'voltage_mV': float }

Uso típico (bloqueante):
	for s in stream_samples(address=0x48, channel=0, pga=1, rate=250):
		print(s)
"""

from __future__ import annotations
import time
from datetime import datetime
from typing import Generator, Optional

try:
	from smbus2 import SMBus
except Exception:  # En entornos sin I2C (PC de desarrollo)
	SMBus = None  # type: ignore

# Registros ADS1115
REG_CONVERSION = 0x00
REG_CONFIG = 0x01

DEFAULT_ADDRESS = 0x48
I2C_BUS = 1

PGA_FS = {
	0: 6.144,
	1: 4.096,
	2: 2.048,
	3: 1.024,
	4: 0.512,
	5: 0.256,
}


def _build_config(mux: int = 0b100, pga: int = 1, mode: int = 0, dr: int = 0b101, comp_que: int = 0b11) -> int:
	os_bit = 1 << 15
	mux_bits = (mux & 0x7) << 12
	pga_bits = (pga & 0x7) << 9
	mode_bit = (mode & 0x1) << 8
	dr_bits = (dr & 0x7) << 5
	comp_mode = 0 << 4
	comp_pol = 0 << 3
	comp_lat = 0 << 2
	comp_que_bits = comp_que & 0x3
	return os_bit | mux_bits | pga_bits | mode_bit | dr_bits | comp_mode | comp_pol | comp_lat | comp_que_bits


def _twobytes_to_int(msb: int, lsb: int) -> int:
	val = (msb << 8) | lsb
	if val & 0x8000:
		return val - (1 << 16)
	return val


def _read_conversion(bus, address: int) -> int:
	data = bus.read_i2c_block_data(address, REG_CONVERSION, 2)
	return _twobytes_to_int(data[0], data[1])


def stream_samples(
	address: int = DEFAULT_ADDRESS,
	channel: int = 0,
	pga: int = 1,
	rate: int = 250,
	i2c_bus: int = I2C_BUS,
) -> Generator[dict, None, None]:
	"""Genera muestras del ADS1115 configurado en modo continuo.

	Requiere ejecutar en Raspberry Pi con I2C habilitado y smbus2 instalado.
	"""
	if SMBus is None:
		raise RuntimeError("smbus2 no disponible. Ejecuta esto en Raspberry Pi con I2C habilitado.")

	dr_map = {128: 0b100, 250: 0b101, 475: 0b110, 860: 0b111}
	dr_bits = dr_map.get(rate, 0b101)
	mux_base = {0: 0b100, 1: 0b101, 2: 0b110, 3: 0b111}.get(channel, 0b100)
	cfg = _build_config(mux=mux_base, pga=pga, mode=0, dr=dr_bits, comp_que=0b11)
	fs_v = PGA_FS.get(pga, 4.096)
	lsb_v = fs_v / 32768.0
	period = 1.0 / float(rate)

	with SMBus(i2c_bus) as bus:
		# Configuración inicial
		bus.write_i2c_block_data(address, REG_CONFIG, [(cfg >> 8) & 0xFF, cfg & 0xFF])
		time.sleep(0.01)
		next_t = time.time()
		while True:
			raw = _read_conversion(bus, address)
			voltage_v = raw * lsb_v
			yield {
				"timestamp": datetime.utcnow().isoformat(timespec='microseconds') + 'Z',
				"raw": int(raw),
				"voltage_mV": float(voltage_v * 1000.0),
			}
			next_t += period
			sleep_t = next_t - time.time()
			if sleep_t > 0:
				time.sleep(sleep_t)
			else:
				next_t = time.time()
