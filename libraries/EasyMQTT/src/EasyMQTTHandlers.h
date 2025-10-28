#ifndef EASYMQTT_HANDLERS_H
#define EASYMQTT_HANDLERS_H

#include <Arduino.h>
#include <functional>

// Handler untuk koneksi
typedef std::function<void()> EasyMQTTConnectedHandler;
typedef std::function<void()> EasyMQTTDisconnectedHandler;

// Handler untuk pesan masuk
typedef std::function<void(const String &topic, const String &payload)> EasyMQTTMessageHandler;

#endif
