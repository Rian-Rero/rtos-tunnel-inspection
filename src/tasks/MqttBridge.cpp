/**
 * @file MqttBridge.cpp
 * @brief Implementação da ponte MQTT para os comandos remotos.
 */
#include "tasks/MqttBridge.hpp"

#include <sys/select.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>

#include "core/TerminalPrinter.hpp"

namespace tasks {

MqttBridge::MqttBridge(std::shared_ptr<core::SharedContext> context) : context_(context) {}

void MqttBridge::handleMessage(const std::string& topic, const std::string& payload) {
    if (topic == "cmd/mode") {
        const std::string normalized = payload;
        const bool manual = normalized == "MANUAL";
        context_->manual_mode.store(manual);
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "MQTT",
                                   "Modo recebido via broker: " + normalized);
        return;
    }

    if (topic == "cmd/speed_sp") {
        try {
            context_->speed_setpoint.store(std::stoi(payload));
        } catch (...) {
            core::TerminalPrinter::Log(core::TerminalPrinter::Level::Warning, "MQTT",
                                       "Setpoint inválido recebido: " + payload);
        }
        return;
    }

    if (topic == "cmd/direction") {
        int direction = 0;
        if (payload == "LEFT") {
            direction = -1;
        } else if (payload == "RIGHT") {
            direction = 1;
        }
        context_->direction.store(direction);
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "MQTT",
                                   "Direção recebida via broker: " + payload);
        return;
    }
}

void MqttBridge::run() {
    const char* command =
        "mosquitto_sub -h localhost -v -t cmd/mode -t cmd/speed_sp -t cmd/direction";
    FILE* pipe = popen(command, "r");
    if (!pipe) {
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Error, "MQTT",
                                   "Falha ao iniciar mosquitto_sub.");
        return;
    }

    int fd = fileno(pipe);
    char buffer[512];

    while (context_->is_running) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(fd, &read_fds);

        timeval timeout;
        timeout.tv_sec = 0;
        timeout.tv_usec = 200000;

        int ready = select(fd + 1, &read_fds, nullptr, nullptr, &timeout);
        if (ready <= 0) {
            continue;
        }

        if (!fgets(buffer, sizeof(buffer), pipe)) {
            break;
        }

        std::string line(buffer);
        if (!line.empty() && line.back() == '\n') {
            line.pop_back();
        }

        const std::size_t separator = line.find(' ');
        if (separator == std::string::npos) {
            continue;
        }

        const std::string topic = line.substr(0, separator);
        const std::string payload = line.substr(separator + 1);
        handleMessage(topic, payload);
    }

    pclose(pipe);
}

}  // namespace tasks