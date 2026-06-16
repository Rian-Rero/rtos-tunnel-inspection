/**
 * @file TaskTimingLogger.hpp
 * @brief Logger de timing por ciclo para provar conformidade de deadlines RTOS.
 */
#pragma once
#include <chrono>
#include <cstdint>
#include <fstream>
#include <mutex>
#include <string>

namespace core {

/**
 * @brief Singleton que registra, por ciclo, o instante agendado vs real de wakeup
 *        e o instante de fim de execução de cada tarefa periódica.
 *
 * CSV gerado: task_name, period_ms, cycle_num, scheduled_ns, actual_ns, exec_end_ns
 *
 * - jitter      = actual_ns   - scheduled_ns  (deve ser ~0 e estável)
 * - exec_time   = exec_end_ns - actual_ns      (deve ser << period_ms * 1e6)
 * - slack       = (scheduled_ns + period_ms*1e6) - exec_end_ns  (deve ser > 0)
 */
class TaskTimingLogger {
   public:
    struct Record {
        const char* task;
        int period_ms;
        uint64_t cycle;
        uint64_t scheduled_ns;
        uint64_t actual_ns;
        uint64_t exec_end_ns;
    };

    static TaskTimingLogger& instance();

    void open(const std::string& path);
    void log(const Record& r);

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
