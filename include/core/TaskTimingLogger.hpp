/**
 * @file TaskTimingLogger.hpp
 * @brief Registrador de temporização por ciclo para provar conformidade de prazos RTOS.
 */
#pragma once
#include <chrono>
#include <cstdint>
#include <fstream>
#include <mutex>
#include <string>

namespace core {

/**
 * @brief Instância única que registra, por ciclo, o instante planejado vs real de despertar
 *        e o instante de fim de execução de cada tarefa periódica.
 *
 * CSV gerado: task_name, period_ms, cycle_num, scheduled_ns, actual_ns, exec_end_ns
 *
 * - desvio      = actual_ns - scheduled_ns  (deve ser ~0 e estável)
 * - execução    = exec_end_ns - actual_ns  (deve ser << period_ms * 1e6)
 * - folga       = (scheduled_ns + period_ms*1e6) - exec_end_ns  (deve ser > 0)
 */
class TaskTimingLogger {
   public:
    /**
     * @brief Registro bruto de temporização de uma execução de tarefa.
     */
    struct Record {
        const char* task;      /**< Nome curto da tarefa registrada. */
        int period_ms;         /**< Período esperado da tarefa em milissegundos. */
        uint64_t cycle;        /**< Número sequencial do ciclo registrado. */
        uint64_t scheduled_ns; /**< Instante planejado de despertar em nanossegundos. */
        uint64_t actual_ns;    /**< Instante real de início em nanossegundos. */
        uint64_t exec_end_ns;  /**< Instante real de fim da execução em nanossegundos. */
    };

    /**
     * @brief Retorna a instância única do registrador.
     * @return Referência para a instância única de TaskTimingLogger.
     */
    static TaskTimingLogger& instance();

    /**
     * @brief Abre o arquivo CSV de temporização e grava o cabeçalho.
     * @param path Caminho do arquivo CSV de saída.
     */
    void open(const std::string& path);

    /**
     * @brief Registra uma linha de temporização no arquivo CSV.
     * @param r Registro de temporização a ser persistido.
     */
    void log(const Record& r);

    /**
     * @brief Converte um ponto de tempo para nanossegundos desde a época do relógio.
     * @tparam TimePoint Tipo do ponto de tempo recebido.
     * @param tp Ponto de tempo a ser convertido.
     * @return Valor em nanossegundos.
     */
    template <typename TimePoint>
    static uint64_t toNs(TimePoint tp) {
        return static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(tp.time_since_epoch()).count());
    }

   private:
    TaskTimingLogger() = default;
    std::ofstream file_;
    std::mutex mutex_;
};

}  // namespace core
