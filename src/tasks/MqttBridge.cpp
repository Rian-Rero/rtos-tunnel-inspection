/**
 * @file MqttBridge.cpp
 * @brief Implementação da ponte MQTT para os comandos remotos.
 */
#include "tasks/MqttBridge.hpp"

#include <signal.h>
#include <sys/select.h>
#include <unistd.h>

#include <algorithm>
#include <cmath>
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
            const int requested = std::clamp(std::stoi(payload), -100, 100);
            if (requested < 0) {
                context_->direction.store(-1);
            }
            context_->speed_setpoint.store(std::abs(requested));
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
    // Wraps the command so the shell prints its own PID before exec'ing mosquitto_sub.
    // After exec, the PID is reused by mosquitto_sub — gives us a handle to kill it on shutdown.
    const char* command =
        "sh -c 'echo $$; exec mosquitto_sub -h localhost -v"
        " -t cmd/mode -t cmd/speed_sp -t cmd/direction'";
    FILE* pipe = popen(command, "r");
    if (!pipe) {
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Error, "MQTT",
                                   "Falha ao iniciar mosquitto_sub.");
        return;
    }

    // First line is the child PID (printed before exec)
    char pid_buf[32] = {};
    pid_t child_pid = -1;
    if (fgets(pid_buf, sizeof(pid_buf), pipe)) {
        child_pid = static_cast<pid_t>(std::atoi(pid_buf));
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

        handleMessage(line.substr(0, separator), line.substr(separator + 1));
    }

    // Kill mosquitto_sub before pclose() so it doesn't block waiting for the child to exit
    if (child_pid > 0) {
        kill(child_pid, SIGKILL);
    }
    pclose(pipe);
}

}  // namespace tasks
