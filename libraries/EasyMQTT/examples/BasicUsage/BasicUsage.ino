#include <EasyMQTT.h>

#define EASY_MQTT_TOKEN "XXXXX"

// Inisialisasi dengan:
EasyMQTT mqtt(EASY_MQTT_TOKEN);

EASYMQTT_WRITE(V0)
{
    Serial.println("Terima dari V0: " + payload);
    EASYMQTT_WRITE_VPIN(V2, "Jawaban ke V2");
}

void setup()
{
    Serial.begin(115200);

    Serial.println("init setup");

    // Hubungkan ke WiFi
    mqtt.begin("WIFI_SSID", "WIFI_PASSWORD");

    // Handler saat terputus dari broker MQTT
    mqtt.onDisconnected([]()
                        { Serial.println("Terputus dari MQTT"); });
}

void loop()
{
    mqtt.loop(); // Penting: proses internal MQTT
}
