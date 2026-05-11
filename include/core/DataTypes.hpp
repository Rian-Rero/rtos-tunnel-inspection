/**
 * @file DataTypes.hpp
 * @brief Definição das estruturas de dados globais do sistema ATR.
 * * Este arquivo contém os pacotes de dados que trafegam pelos buffers IPC
 * (Inter-Process Communication) entre as diferentes threads do sistema.
 */
#pragma once
#include <cstdint>

namespace core {

/**
 * @brief Estrutura que define o comando de movimento do robô.
 */
struct NavigationSetpoint {
    int speed_setpoint; /**< Setpoint de velocidade desejada (-100 a 100%) */
    bool is_automatic; /**< Flag indicando se o robô está em modo autônomo (true) ou manual (false)
                        */
};

/**
 * @brief Estrutura que armazena os dados processados da superfície do túnel.
 */
struct SurfaceData {
    uint64_t timestamp;      /**< Carimbo de tempo da leitura em milissegundos */
    double position_x;       /**< Posição horizontal (X) do robô no túnel em metros */
    double lidar_distance_y; /**< Distância vertical medida pelo sensor LIDAR até o teto */
    double confidence_level; /**< Nível de confiança da medição (0.0 a 1.0) */
};

}  // namespace core