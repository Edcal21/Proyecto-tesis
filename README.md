# 🫀 Proyecto-Tesis: Adquisición ECG con AD8232 + ADS1115 + Raspberry Pi 4

Este proyecto permite capturar señales ECG (electrocardiograma) desde el sensor **AD8232**, digitalizarlas con el conversor **ADS1115** y procesarlas en una **Raspberry Pi 4** usando I2C. Las muestras pueden visualizarse en consola, almacenarse en CSV y analizarse en tiempo real (filtrado y detección de picos R).

---

## 📦 Requisitos de Hardware

- ✅ Raspberry Pi 4 con I2C habilitado (I2C-1)
- ✅ Sensor ECG AD8232
- ✅ ADC ADS1115 (resolución 16 bits, 4 canales analógicos)
- ✅ Cables de conexión dupont (macho-hembra)

---

## 🧪 Conexiones (Wiring)

| Componente       | Raspberry Pi 4 GPIO |
|------------------|---------------------|
| ADS1115 VCC      | 3.3V (pin 1)        |
| ADS1115 GND      | GND (pin 6)         |
| ADS1115 SDA      | GPIO2 / SDA (pin 3) |
| ADS1115 SCL      | GPIO3 / SCL (pin 5) |
| AD8232 OUT       | ADS1115 AIN0        |
| AD8232 GND       | GND                 |
| AD8232 3.3V      | 3.3V                |

---

# 🫀 Proyecto-Tesis: Adquisición ECG con AD8232 + ADS1115 + Raspberry Pi 4

Este proyecto permite capturar señales ECG (electrocardiograma) desde el sensor **AD8232**, digitalizarlas con el conversor **ADS1115** y procesarlas en una **Raspberry Pi 4** usando I2C. Las muestras pueden visualizarse en consola, almacenarse en CSV y analizarse en tiempo real (filtrado y detección de picos R).

---

## 📦 Requisitos de Hardware

- ✅ Raspberry Pi 4 con I2C habilitado (I2C-1)
- ✅ Sensor ECG AD8232
- ✅ ADC ADS1115 (resolución 16 bits, 4 canales analógicos)
- ✅ Cables de conexión dupont (macho-hembra)

---

## 🧪 Conexiones (Wiring)

| Componente       | Raspberry Pi 4 GPIO |
|------------------|---------------------|
| ADS1115 VCC      | 3.3V (pin 1)        |
| ADS1115 GND      | GND (pin 6)         |
| ADS1115 SDA      | GPIO2 / SDA (pin 3) |
| ADS1115 SCL      | GPIO3 / SCL (pin 5) |
| AD8232 OUT       | ADS1115 AIN0        |
| AD8232 GND       | GND                 |
| AD8232 3.3V      | 3.3V                |

---

## 💻 Software y Dependencias

1. Habilitá I2C desde `raspi-config`:
   ```bash
   sudo raspi-config
   # Interfacing Options > I2C > Enable
2. Instalá los paquetes necesarios:
python3 -m pip install -r requirements.txt

3.Ejecutá el script principal:

python3 ecg_ads1115.py


 ⚙️ Funcionalidades

 | Opción                 | Descripción                                                |
| ---------------------- | ---------------------------------------------------------- |
| `--output archivo.csv` | Guarda las lecturas en formato CSV                         |
| `--filter`             | Aplica un filtro pasa-altas (~0.5 Hz) + suavizado (~40 Hz) |
| `--detect`             | Detecta picos R (requiere usar también `--filter`)         |




🧪 Salida del script


Los datos se imprimen en consola o se guardan como CSV con las siguientes columnas:



timestamp_utc, raw_adc, voltage_mV, [filtered_mV], [r_peak]
Las columnas filtered_mV y r_peak aparecen solo si se usan los flags --filter y --detect.

▶️ Ejemplos de Uso
🔹 Leer señal cruda a 250 SPS (por defecto)

python3 ecg_ads1115.py
Filtrar señal y guardar en archivo
python3 ecg_ads1115.py --output ecg_log.csv --filter


 🔹 Detectar picos R y registrar resultado

 python3 ecg_ads1115.py --output ecg_log.csv --filter --detect


📌 Notas técnicas

Se utiliza el modo continuo del ADS1115 a 250 muestras/segundo.

Para máxima precisión, asegurá:

Uso de cables cortos

Buena referencia a tierra

Evitar interferencias por USB o WiFi

No se realiza análisis médico ni diagnóstico. Este sistema es solo educativo.


📄 Licencia

MIT © Emorie Aguirre - UNI 
Este proyecto puede ser usado, modificado y distribuido libremente con fines educativos y de investigación



