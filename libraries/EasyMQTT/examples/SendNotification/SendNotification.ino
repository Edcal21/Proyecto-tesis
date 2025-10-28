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
