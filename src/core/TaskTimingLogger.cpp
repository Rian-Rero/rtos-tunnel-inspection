/**
 * @file TaskTimingLogger.cpp
 * @brief Implementação do registrador de temporização por ciclo.
 */
#include "core/TaskTimingLogger.hpp"

namespace core {

TaskTimingLogger& TaskTimingLogger::instance() {
    static TaskTimingLogger inst;
    return inst;
}

void TaskTimingLogger::open(const std::string& path) {
    std::lock_guard<std::mutex> lock(mutex_);
    file_.open(path, std::ios::out | std::ios::trunc);
    if (file_.is_open()) {
        file_ << "task_name,period_ms,cycle_num,scheduled_ns,actual_ns,exec_end_ns\n";
    }
}

void TaskTimingLogger::log(const Record& r) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!file_.is_open())
        return;
    file_ << r.task << ',' << r.period_ms << ',' << r.cycle << ',' << r.scheduled_ns << ','
          << r.actual_ns << ',' << r.exec_end_ns << '\n';
}

}  // namespace core
