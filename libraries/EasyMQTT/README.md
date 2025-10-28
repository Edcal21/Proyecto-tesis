# 🚀 EasyMQTT for ESP32 / ESP8266

EasyMQTT adalah library MQTT untuk ESP32 yang dirancang agar **mudah digunakan** seperti Blynk, tetapi dengan protokol **MQTT + SSL/TLS**.  
Library ini terintegrasi langsung dengan aplikasi **EasyLife IoT** untuk memudahkan kontrol dan monitoring perangkat IoT secara real-time.

![Arsitektur EasyMQTT](https://api.easylife.biz.id/public/images/diagram-easymqtt.png)


---

## ✨ Fitur Utama
- 🔄 Auto reconnect WiFi & MQTT
- 🔐 SSL/TLS bawaan (Let's Encrypt ISRG Root X1)
- 🖐 Gaya handler mirip Blynk: `EASY_WRITE(v1)`
- 📡 Mendukung OTA update via HTTPS (`setInsecure()` opsional)
- 📱 Terhubung langsung ke aplikasi **EasyLife IoT**
- 📊 Format topic fleksibel: `user/device/v1` hingga `v100`

---

## 📦 Instalasi Library

### 🔹 Arduino IDE
1. Buka **Arduino IDE**
2. Masuk menu **Sketch → Include Library → Manage Libraries…**
3. Pada kolom pencarian, ketik **EasyMQTT**
4. Pilih **EasyMQTT** dari daftar hasil pencarian lalu klik **Install**

### PlatformIO
1. **Buka PlatformIO IDE** di VSCode atau Atom.
2. Di sidebar kiri, klik ikon **PlatformIO Home** (ikon rumah).
3. Pilih menu **Libraries**.
4. Pada kolom pencarian, ketik nama library yang ingin diinstal.
5. Setelah muncul hasil pencarian, pilih library yang sesuai.
6. Klik tombol **Install** untuk memasang library ke project yang sedang aktif.
7. Tunggu proses instalasi selesai.

**Catatan:**

* Library yang diinstal lewat Library Manager akan otomatis tersedia di project, cukup dengan `#include` di kode.

* Jika ingin instalasi manual, bisa lewat file `platformio.ini` dengan menambahkan:

  ```ini
  lib_deps =
    nama/library
  ```

  lalu jalankan `pio run` untuk mengunduh dan menginstal library.

---

## 🛠 Cara Menggunakan EasyMQTT
- **EASY_MQTT_TOKEN** isi dengan token device pada aplikasi **Easlife-IoT**, menu perangkat dapat dilihat pada menu **home->buka_sidebar->Perangkat->Pilih_perangkat/device ESP->Token Device**

- **Virtual PIN** tersedia dari **V0** sampai **V100**

### 💻 Basic Usage
```cpp
#include <EasyMQTT.h>

#define EASY_MQTT_TOKEN "XXXXX"

// Inisialisasi dengan:
EasyMQTT mqtt(EASY_MQTT_TOKEN);

EASYMQTT_WRITE(V0) {
    Serial.println("Terima dari V0: " + payload);
    EASYMQTT_WRITE_VPIN(V2, "Jawaban ke V2");
}

void setup() {
    Serial.begin(115200);

    Serial.println("init setup");

    // Hubungkan ke WiFi
    mqtt.begin("WIFI_SSID", "WIFI_PASSWORD");

    // Handler saat terputus dari broker MQTT
    mqtt.onDisconnected([]() { Serial.println("Terputus dari MQTT"); });
}

void loop() {
    mqtt.loop();  // Penting: proses internal MQTT
}
```

### 📳 Send Notification
```cpp
#include <EasyMQTT.h>

#define EASY_MQTT_TOKEN "XXXXX"

// Inisialisasi EasyMQTT
EasyMQTT mqtt(EASY_MQTT_TOKEN);

void setup()
{
    Serial.begin(115200);

    // Mulai koneksi WiFi & MQTT
    mqtt.begin(WIFI_SSID, WIFI_PASSWORD);

    // Callback ketika berhasil terkoneksi ke MQTT
    mqtt.onConnected([]()
                     {
    Serial.println("Terhubung ke MQTT");

    // Kirim notifikasi saat terkoneksi
    mqtt.sendNotification("ESP32 Aktif", "Perangkat baru saja online"); });

    // Callback jika koneksi terputus
    mqtt.onDisconnected([]()
                        { Serial.println("Terputus dari MQTT"); });
}

void loop()
{
    mqtt.loop();

    // Contoh kirim notifikasi setiap 10 detik (hanya demo)
    static unsigned long lastNotify = 0;
    if (millis() - lastNotify > 10000)
    {
        lastNotify = millis();
        mqtt.sendNotification("Notifikasi Rutin", "Ini adalah pesan setiap 10 detik");
    }
}
```
### 🔄 OTA Update
```cpp
Comming soon
```
---
## 📲 Cara Menggunakan EasyLife IoT

### Step 1: Buat Project di EasyLife IoT

1. **Login** ke dashboard EasyLife IoT di browser.
2. Cari menu **Projects** di sidebar.
3. Klik tombol **Add Project** atau **+ New Project**.
4. Isi nama project, contoh: `SmartHome`.
5. Klik **Save**.

### Step 2: Buat Dashboard dalam Project

1. Masuk ke halaman project yang baru dibuat.
2. Pilih menu **Dashboards**.
3. Klik tombol **Add Dashboard**.
4. Isi nama dashboard, contoh: `Dashboard Ruang Tamu`.
5. Klik **Save**.

### Step 3: Daftarkan Device

1. Masih di dalam project, pilih menu **Devices**.
2. Klik **Add Device**.
3. Isi nama device, contoh: `ESP32 Sensor 1`.
4. Klik **Save**.
5. Setelah device terbuat, **salin Device Token** yang muncul (ini akan dipakai di kode ESP).

### Step 4: Setup Kode ESP dengan Token

1. Buka IDE (Arduino IDE atau PlatformIO).
2. Siapkan kode ESP berikut (contoh ESP32 + EasyMQTT):

```cpp
#include <EasyMQTT.h>

#define EASY_MQTT_TOKEN "TOKEN_DEVICE_YANG_KAMU_SALIN"

// Inisialisasi dengan:
EasyMQTT mqtt(EASY_MQTT_TOKEN);

EASYMQTT_WRITE(V0) {
    Serial.println("Terima dari V0: " + payload);
    EASYMQTT_WRITE_VPIN(V2, "Jawaban ke V2");
}

void setup() {
    Serial.begin(115200);

    Serial.println("init setup");

    // Hubungkan ke WiFi
    mqtt.begin("WIFI_SSID", "WIFI_PASSWORD");

    // Handler saat terputus dari broker MQTT
    mqtt.onDisconnected([]() { Serial.println("Terputus dari MQTT"); });
}

void loop() {
    mqtt.loop();  // Penting: proses internal MQTT
}
```

3. Ganti `ssid`, `password`, dan `EASY_MQTT_TOKEN` sesuai milikmu.
4. Upload kode ke ESP.

### Step 5: Cek Koneksi Device di Dashboard

* Di dashboard EasyLife IoT, buka menu **Devices** → Device yang kamu buat.
* Pastikan status device muncul **Online**.
* Jika serial monitor ESP menunjukkan `MQTT Connected`, berarti sudah berhasil.

### Step 6: Tambah Widget ke Dashboard

1. Masuk ke **Dashboard** yang sudah dibuat.
2. Klik tombol **Add Widget** atau `+`.
3. Pilih jenis widget, misalnya **Value Display** untuk menampilkan angka suhu.
4. Pilih device `ESP32 Sensor 1`.
5. Pilih virtual pin, misalnya `vPin 1`.
6. Isi label widget, misal: `Suhu Ruang`.
7. Simpan widget.

### Step 7: Lihat Data di Dashboard

* Tunggu beberapa saat.
* Widget akan otomatis menampilkan data yang dikirim ESP ke virtual pin 1.
* Data akan update sesuai interval kirim data dari ESP.

![Arsitektur EasyMQTT](https://api.easylife.biz.id/public/images/sample_dashboard.png)


### Tips tambahan

* Kamu bisa buat banyak widget dengan berbagai virtual pin.
* Bisa juga menambahkan widget tombol untuk mengirim perintah ke device.
* Virtual pin bersifat fleksibel untuk berbagai tipe data (angka, teks, status).

---
