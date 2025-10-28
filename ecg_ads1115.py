#!/usr/bin/env python3
"""
Lectura en tiempo real de un sensor ECG AD8232 conectado a un ADC ADS1115 via I2C.
- Raspberry Pi 4 (I2C bus 1)
- ADS1115 configurado en modo continuo a 250 SPS

Salida: CSV a consola: timestamp, raw_adc, voltage_mV

Ejemplo de uso:
  python3 ecg_ads1115.py

Requiere: smbus2
"""

import time
import argparse
from smbus2 import SMBus
import signal
import sys
from datetime import datetime
import csv
from collections import deque
import math

# ADS1115 registers
REG_CONVERSION = 0x00
REG_CONFIG = 0x01

# Default I2C address for ADS1115
DEFAULT_ADDRESS = 0x48
I2C_BUS = 1  # Raspberry Pi 4

# PGA full-scale ranges (bits 11:9)
PGA_FS = {
    0: 6.144,
    1: 4.096,
    2: 2.048,
    3: 1.024,
    4: 0.512,
    5: 0.256,
}

running = True


def build_config(mux=0b100, pga=1, mode=0, dr=0b101, comp_que=0b11):
    """Construye el valor de configuración de 16 bits para el ADS1115.
    Parámetros principales:
      mux: 3 bits MUX (ej. 0b100 = AIN0 vs GND)
      pga: 3 bits PGA (0..5) index en PGA_FS
      mode: 0=continuous, 1=single-shot
      dr: 3 bits data rate (101 = 250 SPS)
      comp_que: 2 bits para deshabilitar comparador (0b11)
    Devuelve: entero 0..0xFFFF
    """
    os_bit = 1 << 15  # poner 1 para iniciar conversion (ok en continuous)
    mux_bits = (mux & 0x7) << 12
    pga_bits = (pga & 0x7) << 9
    mode_bit = (mode & 0x1) << 8
    dr_bits = (dr & 0x7) << 5
    comp_mode = 0 << 4
    comp_pol = 0 << 3
    comp_lat = 0 << 2
    comp_que_bits = comp_que & 0x3
    cfg = os_bit | mux_bits | pga_bits | mode_bit | dr_bits | comp_mode | comp_pol | comp_lat | comp_que_bits
    return cfg


def twobytes_to_int(msb, lsb):
    val = (msb << 8) | lsb
    # Convertir a signed 16-bit
    if val & 0x8000:
        return val - (1 << 16)
    return val


def read_conversion(bus, address):
    data = bus.read_i2c_block_data(address, REG_CONVERSION, 2)
    return twobytes_to_int(data[0], data[1])


def signal_handler(sig, frame):
    global running
    running = False
    print("\nDeteniendo lectura...")


def main():
    parser = argparse.ArgumentParser(description="Lectura ECG AD8232 vía ADS1115 a 250 SPS")
    parser.add_argument("--address", type=lambda x: int(x,0), default=DEFAULT_ADDRESS,
                        help="Dirección I2C del ADS1115 (hex), por defecto 0x48")
    parser.add_argument("--pga", type=int, choices=range(0,6), default=1,
                        help="Index PGA (0..5). 1=±4.096V por defecto")
    parser.add_argument("--channel", type=int, choices=[0,1,2,3], default=0,
                        help="Canal AINx a usar (0..3). Por defecto AIN0")
    parser.add_argument("--rate", type=int, default=250,
                        help="Tasa de muestreo objetivo en SPS (solo 250,475,860 o similares son soportados por ADS1115)")
    parser.add_argument("--output", type=str, default=None,
                        help="Archivo CSV de salida (si no se especifica, sólo consola)")
    parser.add_argument("--filter", action="store_true",
                        help="Habilitar filtrado simple en tiempo real (HP 0.5 Hz + MA lowpass ~40 Hz)")
    parser.add_argument("--detect", action="store_true",
                        help="Habilitar detección simple de picos R (requiere --filter)")
    parser.add_argument("--threshold-factor", type=float, default=3.0,
                        help="Factor multiplicador para el umbral de detección R sobre la media del envolvente absoluto")
    args = parser.parse_args()

    # Map rate to DR bits; support 250, 475, 860, 128 (fallback)
    dr_map = {128: 0b100, 250: 0b101, 475: 0b110, 860: 0b111}
    if args.rate in dr_map:
        dr_bits = dr_map[args.rate]
    else:
        print(f"Aviso: tasa {args.rate} SPS no mapeada; usando 250 SPS por defecto")
        dr_bits = dr_map[250]

    # MUX for single-ended AINx: AIN0=100, AIN1=101, AIN2=110, AIN3=111
    mux_base = {0:0b100, 1:0b101, 2:0b110, 3:0b111}[args.channel]

    # Build config
    cfg = build_config(mux=mux_base, pga=args.pga, mode=0, dr=dr_bits, comp_que=0b11)

    # Compute volts per count
    fs_v = PGA_FS.get(args.pga, 4.096)
    lsb = fs_v / 32768.0  # V per LSB

    print(f"Iniciando lectura ADS1115 @ 0x{args.address:02X}, canal AIN{args.channel}, PGA index {args.pga} (±{fs_v} V), DR_bits={bin(dr_bits)}")
    print("Timestamp,raw,voltage_mV")

    signal.signal(signal.SIGINT, signal_handler)

    with SMBus(I2C_BUS) as bus:
        # Write config register (2 bytes, MSB first)
        cfg_msb = (cfg >> 8) & 0xFF
        cfg_lsb = cfg & 0xFF
        bus.write_i2c_block_data(args.address, REG_CONFIG, [cfg_msb, cfg_lsb])

        # Small delay to allow conversion register to be populated
        time.sleep(0.01)

        period = 1.0 / args.rate
        next_time = time.time()
        count = 0
        # Setup output file if requested
        csv_file = None
        csv_writer = None
        if args.output:
            csv_file = open(args.output, 'w', newline='')
            csv_writer = csv.writer(csv_file)
            # header
            csv_writer.writerow(['timestamp_utc','raw','voltage_mV','filtered_mV','r_detected'])

        # Filtering state (simple HP + moving average LP)
        if args.filter:
            fs = args.rate
            dt = 1.0 / fs
            # High-pass single-pole cutoff fc_hp (Hz)
            fc_hp = 0.5
            tau = 1.0 / (2 * math.pi * fc_hp)
            alpha_hp = tau / (tau + dt)
            hp_x_prev = 0.0
            hp_y_prev = 0.0
            # Moving average lowpass window size for ~40 Hz
            lp_cut = 40.0
            ma_N = max(1, int(round(fs / lp_cut)))
            ma_buf = deque([0.0]*ma_N, maxlen=ma_N)
            ma_sum = 0.0
            # Envelope smoothing for detection
            env_N = max(1, int(round(0.05 * fs)))  # 50 ms
            env_buf = deque([0.0]*env_N, maxlen=env_N)
            env_sum = 0.0

        # Detection state
        r_refractory_s = 0.2  # 200 ms
        last_r_time = -1.0
        while running:
            raw = read_conversion(bus, args.address)
            voltage = raw * lsb  # in volts
            ts = datetime.utcnow().isoformat(timespec='microseconds') + 'Z'
            filtered_mV = None
            r_detected = False
            voltage_mV = voltage * 1000.0

            if args.filter:
                # High-pass (single-pole) on voltage (V)
                x = voltage
                y_hp = alpha_hp * (hp_y_prev + x - hp_x_prev)
                hp_x_prev = x
                hp_y_prev = y_hp
                # Low-pass via moving average (on hp output), convert to mV
                val_mV = y_hp * 1000.0
                if len(ma_buf) < ma_N:
                    ma_buf.append(val_mV)
                    ma_sum += val_mV
                    lp = ma_sum / len(ma_buf)
                else:
                    # rotate
                    oldest = ma_buf[0]
                    ma_sum -= oldest
                    ma_buf.append(val_mV)
                    ma_sum += val_mV
                    lp = ma_sum / ma_N
                filtered_mV = lp

                if args.detect:
                    # envelope = moving average of absolute value
                    abs_v = abs(filtered_mV)
                    if len(env_buf) < env_N:
                        env_buf.append(abs_v)
                        env_sum += abs_v
                        env = env_sum / len(env_buf)
                    else:
                        oldest_e = env_buf[0]
                        env_sum -= oldest_e
                        env_buf.append(abs_v)
                        env_sum += abs_v
                        env = env_sum / env_N

                    threshold = max(0.1, env * args.threshold_factor)  # mV threshold floor
                    now = time.time()
                    if abs_v >= threshold and (now - last_r_time) > r_refractory_s:
                        r_detected = True
                        last_r_time = now

            # Print CSV to console
            if filtered_mV is None:
                print(f"{ts},{raw},{voltage*1000:.3f}")
                if csv_writer:
                    csv_writer.writerow([ts, raw, f"{voltage*1000:.3f}", '', ''])
            else:
                print(f"{ts},{raw},{voltage*1000:.3f},{filtered_mV:.3f},{int(r_detected)}")
                if csv_writer:
                    csv_writer.writerow([ts, raw, f"{voltage*1000:.3f}", f"{filtered_mV:.3f}", int(r_detected)])

            count += 1
            # Schedule next read
            next_time += period
            sleep_time = next_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # We're behind; don't sleep (drift will accumulate little by little)
                next_time = time.time()

        if csv_file:
            csv_file.close()

    print("Lectura finalizada.")


if __name__ == '__main__':
    main()
