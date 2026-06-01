/**
 * @file MqttBridge.hpp
 * @brief Declaração da ponte MQTT para os comandos remotos.
 */
#pragma once

#include <memory>

#include "core/SharedContext.hpp"
#include "tasks/Itask.hpp"

namespace tasks {

/**
 * @class MqttBridge
 * @brief Faz a ponte entre o broker MQTT e o contexto compartilhado do C++.
 */
class MqttBridge : public ITask {
   private:
    std::shared_ptr<core::SharedContext> context_;

    void handleMessage(const std::string& topic, const std::string& payload);

   public:
    explicit MqttBridge(std::shared_ptr<core::SharedContext> context);
    void run() override;
};

}  // namespace tasks