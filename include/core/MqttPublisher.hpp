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

    static std::string escapeForShell(const std::string& value) {
        std::string escaped;
        escaped.reserve(value.size() + 8);
        for (char ch : value) {
            if (ch == '\'') {
                escaped += "'\"'\"'";
            } else {
                escaped += ch;
            }
        }
        return escaped;
    }

   public:
    explicit MqttPublisher(const std::string& topic) {
        const std::string command =
            "mosquitto_pub -h localhost -q 2 -t '" + escapeForShell(topic) + "' -l";
        pipe_ = popen(command.c_str(), "w");
    }

    ~MqttPublisher() {
        if (pipe_ != nullptr) {
            pclose(pipe_);
        }
    }

    MqttPublisher(const MqttPublisher&) = delete;
    MqttPublisher& operator=(const MqttPublisher&) = delete;

    bool publish(const std::string& payload) {
        if (pipe_ == nullptr) {
            return false;
        }
        if (std::fputs(payload.c_str(), pipe_) == EOF) {
            return false;
        }
        if (std::fputc('\n', pipe_) == EOF) {
            return false;
        }
        return std::fflush(pipe_) == 0;
    }
};

}  // namespace core
