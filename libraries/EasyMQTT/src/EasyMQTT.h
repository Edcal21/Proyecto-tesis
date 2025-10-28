#ifndef EASYMQTT_H
#define EASYMQTT_H

#define EASYMQTT_LOG(msg) Serial.println(String("[EasyMQTT] ") + msg)

#if defined(ESP32)
#include <WiFi.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#else
#error "EasyMQTT saat ini hanya mendukung ESP32 dan ESP8266."
#endif

#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "EasyMQTTHandlers.h"
#include "EasyMQTTVPin.h"
#include <map>
#include <Arduino.h>
#include <functional>
#include <vector>

// macro
#define EASYMQTT_WRITE(pin)                                                   \
  void _easyMqttWriteHandler_##pin(String payload);                           \
  __attribute__((constructor)) static void _autoRegister_##pin()              \
  {                                                                           \
    EasyMQTT::_pendingHandlers.push_back({pin, _easyMqttWriteHandler_##pin}); \
  }                                                                           \
  void _easyMqttWriteHandler_##pin(String payload)

#ifndef EASYMQTT_WRITE_VPIN
#define EASYMQTT_WRITE_VPIN(vpin, msg) mqtt.publish(#vpin, msg)
#endif

#ifndef EASYMQTT_WRITE_CUSTOM
#define EASYMQTT_WRITE_CUSTOM(user, device, vpin, msg) mqtt.publish(user, device, #vpin, msg)
#endif

// init class
typedef std::function<void(String)> EasyMQTTCallback;

class EasyMQTT
{
public:
  EasyMQTT(const char *token);
  static EasyMQTT &getInstance();
  void begin();
  void begin(const char *ssid, const char *password);
  void loop();
  void subscribe(const String &virtualPin, EasyMQTTCallback callback);
  void publish(const String &virtualPin, const String &payload);
  void publish(const String &user, const String &device, const String &virtualPin, const String &payload);
  void onConnected(EasyMQTTConnectedHandler handler);
  void onDisconnected(EasyMQTTDisconnectedHandler handler);
  void onMessage(EasyMQTTMessageHandler handler);
  void sendNotification(const String &title, const String &message);
  void updateFirmware(const String &url, bool allowInsecure = false);
  bool isConnected();
  bool fetchDeviceConfig();
  void attachVirtualPin(int vpin, EasyMQTTCallback callback);
  void registerPendingHandlers();

  struct PendingHandler
  {
    int vpin;
    EasyMQTTCallback callback;
  };

  static std::vector<PendingHandler> _pendingHandlers;

private:
  void reconnect();
  String getTopic(const String &vpin);

  String _user;
  String _device;
  String _mqttServer;
  String _mqttUser;
  String _mqttPassword;
  String _token;
  String _mqttToken;
  String _rootCA;
  String _fingerPrint;

  int _mqttPort;

  WiFiClientSecure _secureClient;
  PubSubClient _client;

  std::map<String, EasyMQTTCallback> _callbacks;

  EasyMQTTConnectedHandler connectedCallback;
  EasyMQTTDisconnectedHandler disconnectedCallback;
  EasyMQTTMessageHandler messageCallback;
};

#endif
