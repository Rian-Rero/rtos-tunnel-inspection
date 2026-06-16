/**
 * @file SharedContext.hpp
 * @brief Contexto compartilhado atuando como Broker de estados e sensores.
 */
#pragma once
#include <atomic>
#include <condition_variable>
#include <mutex>

namespace core {

/**
 * @class SharedContext
 * @brief Gerencia os estados globais e atua como um Broker (simulando MQTT) para sensores.
 */
class SharedContext {
   private:
    std::mutex anomaly_mutex_;
    std::condition_variable anomaly_cv_;
    bool anomaly_detected_{false};

   public:
    std::atomic<bool> is_running{true}; /**< Flag global para encerramento gracioso */

    /**
     * @brief Velocidade atual simulada da planta física (motor real).
     * @details Tópico simulado: "/motor/velocidade_real". Lida apenas pelo Encoder.
     */
    std::atomic<double> current_speed{0.0};

    /**
     * @brief Indica se o robô está em modo manual (true) ou automático (false).
     */
    std::atomic<bool> manual_mode{false};

    /**
     * @brief Setpoint de velocidade recebido via MQTT.
     */
    std::atomic<int> speed_setpoint{50};

    /**
     * @brief Direção recebida via MQTT: -1 = LEFT, 0 = STOP, 1 = RIGHT.
     */
    std::atomic<int> direction{0};

    /**
     * @brief Inclinação simulada do túnel em graus, usada como leitura do sensor IMU.
     */
    std::atomic<double> imu_degrees{0.0};

    /**
     * @brief Odometria atual calculada pelo Encoder (em metros).
     * @details Tópico simulado: "/sensor/odometria". Consumida pelo LIDAR e outros módulos.
     */
    std::atomic<double> current_odometry{0.0};

    /**
     * @brief Sinaliza a detecção de uma anomalia estrutural (buraco/saliência).
     */
    void triggerAnomaly();

    /**
     * @brief Redefine o estado de anomalia para falso após a inspeção.
     */
    void resetAnomaly();

    /**
     * @brief Suspende a thread até que uma anomalia seja detectada.
     */
    void waitForAnomaly();

    /**
     * @brief Verifica ativamente se há uma anomalia ocorrendo neste momento.
     */
    bool isAnomalyActive();
};

}  // namespace core
