/**
 * @file ITask.hpp
 * @brief Definição da interface base para todas as tarefas cíclicas.
 */
#pragma once

namespace tasks {
/**
 * @class ITask
 * @brief Interface padrão que todas as tarefas do robô devem implementar.
 */
class ITask {
   public:
    virtual ~ITask() = default;

    /**
     * @brief Método principal onde o loop infinito da thread deve ser implementado.
     */
    virtual void run() = 0;
};
}  // namespace tasks