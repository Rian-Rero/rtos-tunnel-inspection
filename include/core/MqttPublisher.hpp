/**
 * @file MqttPublisher.hpp
 * @brief Publisher MQTT leve baseado em um processo mosquitto_pub persistente.
 */
#pragma once

#include <cstdio>
#include <string>

namespace core {

class MqttPublisher {
   private:
    FILE* pipe_{nullptr};

    static std::string escapeForShell(const std::string& value);

   public:
    explicit MqttPublisher(const std::string& topic);

    ~MqttPublisher();

    MqttPublisher(const MqttPublisher&) = delete;
    MqttPublisher& operator=(const MqttPublisher&) = delete;

    bool publish(const std::string& payload);
};

}  // namespace core
