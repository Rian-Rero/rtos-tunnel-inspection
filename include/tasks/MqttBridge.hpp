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
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */

    /**
     * @brief Processa uma mensagem MQTT recebida e atualiza o contexto compartilhado.
     * @param topic Tópico MQTT da mensagem recebida.
     * @param payload Conteúdo textual da mensagem recebida.
     */
    void handleMessage(const std::string& topic, const std::string& payload);

   public:
    /**
     * @brief Construtor da ponte MQTT.
     * @param context Ponteiro compartilhado para o contexto global.
     */
    explicit MqttBridge(std::shared_ptr<core::SharedContext> context);

    /**
     * @brief Executa o loop principal de consumo dos comandos MQTT.
     */
    void run() override;
};

}  // namespace tasks
