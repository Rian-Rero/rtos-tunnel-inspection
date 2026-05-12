/**
 * @file TerminalPrinter.cpp
 * @brief Implementação do utilitário de impressão estilizada.
 */
#include "core/TerminalPrinter.hpp"

#include <algorithm>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>

namespace core {
namespace {
constexpr const char* kReset = "\033[0m";
constexpr const char* kBold = "\033[1m";
constexpr const char* kDim = "\033[2m";
constexpr const char* kRed = "\033[31m";
constexpr const char* kGreen = "\033[32m";
constexpr const char* kYellow = "\033[33m";
constexpr const char* kBlue = "\033[34m";
constexpr const char* kCyan = "\033[36m";
constexpr const char* kWhite = "\033[37m";

std::mutex& OutputMutex() {
    static std::mutex mutex;
    return mutex;
}
}  // namespace

std::string TerminalPrinter::Timestamp() {
    const auto now = std::chrono::system_clock::now();
    const auto now_time = std::chrono::system_clock::to_time_t(now);
    std::tm local_tm{};
#ifdef _WIN32
    localtime_s(&local_tm, &now_time);
#else
    localtime_r(&now_time, &local_tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&local_tm, "%H:%M:%S");
    return oss.str();
}

const char* TerminalPrinter::LevelLabel(Level level) {
    switch (level) {
        case Level::Info:
            return "INFO";
        case Level::Success:
            return "OK";
        case Level::Warning:
            return "WARN";
        case Level::Error:
            return "ERR";
        case Level::Debug:
            return "DBG";
        default:
            return "LOG";
    }
}

const char* TerminalPrinter::LevelColor(Level level) {
    switch (level) {
        case Level::Info:
            return kCyan;
        case Level::Success:
            return kGreen;
        case Level::Warning:
            return kYellow;
        case Level::Error:
            return kRed;
        case Level::Debug:
            return kBlue;
        default:
            return kWhite;
    }
}

std::string TerminalPrinter::CenterText(const std::string& text, size_t width) {
    if (text.size() >= width) {
        return text;
    }
    const size_t padding = (width - text.size()) / 2;
    const size_t extra = width - text.size() - padding;
    return std::string(padding, ' ') + text + std::string(extra, ' ');
}

void TerminalPrinter::PrintLine(const std::string& line) {
    std::lock_guard<std::mutex> lock(OutputMutex());
    std::cout << line << std::endl;
}

void TerminalPrinter::Banner(const std::string& title, const std::string& subtitle) {
    const size_t width = std::max<size_t>(48, title.size() + 10);
    const std::string line(width, '=');
    PrintLine(std::string(kBold) + kBlue + line + kReset);
    PrintLine(std::string(kBold) + CenterText(title, width) + kReset);
    if (!subtitle.empty()) {
        PrintLine(std::string(kDim) + CenterText(subtitle, width) + kReset);
    }
    PrintLine(std::string(kBold) + kBlue + line + kReset);
}

void TerminalPrinter::Section(const std::string& title) {
    const size_t width = std::max<size_t>(36, title.size() + 8);
    const std::string line(width, '-');
    PrintLine(std::string(kBlue) + line + kReset);
    PrintLine(std::string(kBold) + CenterText(title, width) + kReset);
    PrintLine(std::string(kBlue) + line + kReset);
}

void TerminalPrinter::Log(Level level, const std::string& scope, const std::string& message) {
    std::ostringstream oss;
    oss << kDim << "[" << Timestamp() << "]" << kReset << " " << kBold << LevelColor(level) << "["
        << LevelLabel(level) << "]" << kReset;

    if (!scope.empty()) {
        oss << " " << kBlue << "[" << scope << "]" << kReset;
    }

    oss << " " << message;
    PrintLine(oss.str());
}

void TerminalPrinter::Log(Level level, const std::string& message) { Log(level, "", message); }

void TerminalPrinter::Plain(const std::string& message) { PrintLine(message); }

}  // namespace core
