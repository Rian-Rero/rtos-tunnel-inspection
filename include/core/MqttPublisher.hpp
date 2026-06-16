/**
 * @file MqttPublisher.hpp
 * @brief Publicador MQTT leve baseado em um processo mosquitto_pub persistente.
 */
#pragma once

#include <cstdio>
#include <string>

namespace core {

/**
 * @class MqttPublisher
 * @brief Publicador MQTT leve que mantém um processo `mosquitto_pub` aberto.
 *
 * @details A classe escreve mensagens em modo linha para o stdin do processo
 * `mosquitto_pub`, evitando recriar o processo a cada publicação.
 */
class MqttPublisher {
   private:
    FILE* pipe_{nullptr}; /**< Canal de escrita para o processo `mosquitto_pub`. */

    /**
     * @brief Escapa aspas simples para uso seguro no comando de terminal.
     * @param value Texto original a ser usado como argumento do comando.
     * @return Texto com aspas simples escapadas.
     */
    static std::string escapeForShell(const std::string& value);

   public:
    /**
     * @brief Cria um publicador persistente para um tópico MQTT.
     * @param topic Tópico MQTT onde as mensagens serão publicadas.
     */
    explicit MqttPublisher(const std::string& topic);

    /**
     * @brief Encerra o processo `mosquitto_pub` associado ao publicador.
     */
    ~MqttPublisher();

    /**
     * @brief Impede cópia para preservar a posse única do canal de escrita.
     */
    MqttPublisher(const MqttPublisher&) = delete;

    /**
     * @brief Impede atribuição por cópia para preservar a posse única do canal de escrita.
     */
    MqttPublisher& operator=(const MqttPublisher&) = delete;

    /**
     * @brief Publica uma mensagem no tópico configurado.
     * @param payload Conteúdo textual da mensagem MQTT.
     * @return true se a mensagem foi escrita e descarregada no canal; false em caso de erro.
     */
    bool publish(const std::string& payload);
};

}  // namespace core
