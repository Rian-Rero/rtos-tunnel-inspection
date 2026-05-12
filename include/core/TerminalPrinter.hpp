/**
 * @file TerminalPrinter.hpp
 * @brief Utilitário para impressão padronizada e estilizada no terminal.
 */
#pragma once

#include <string>

namespace core {

/**
 * @class TerminalPrinter
 * @brief Centraliza logs e banners com padrão visual consistente.
 *
 * @details Fornece níveis de severidade, carimbo de tempo e blocos de destaque
 * para facilitar a leitura durante a execução em tempo real.
 */
class TerminalPrinter {
   public:
    /**
     * @brief Níveis de severidade para logs.
     */
    enum class Level {
        Info,    /**< Informação geral */
        Success, /**< Operação concluída com sucesso */
        Warning, /**< Aviso de atenção */
        Error,   /**< Erro crítico */
        Debug    /**< Informações de depuração */
    };

    /**
     * @brief Imprime um banner de abertura com título e subtítulo opcionais.
     * @param title Texto principal do banner.
     * @param subtitle Texto secundário abaixo do título (opcional).
     */
    static void Banner(const std::string& title, const std::string& subtitle = "");

    /**
     * @brief Imprime um divisor de seção com título centralizado.
     * @param title Texto da seção.
     */
    static void Section(const std::string& title);

    /**
     * @brief Imprime um log formatado com nível, escopo e mensagem.
     * @param level Nível de severidade.
     * @param scope Nome curto do subsistema (ex: "Câmera", "Coletor").
     * @param message Conteúdo da mensagem.
     */
    static void Log(Level level, const std::string& scope, const std::string& message);

    /**
     * @brief Imprime um log formatado sem escopo.
     * @param level Nível de severidade.
     * @param message Conteúdo da mensagem.
     */
    static void Log(Level level, const std::string& message);

    /**
     * @brief Imprime uma linha simples sem decoração.
     * @param message Texto a ser impresso.
     */
    static void Plain(const std::string& message);

   private:
    TerminalPrinter() = delete;

    static std::string Timestamp();
    static const char* LevelLabel(Level level);
    static const char* LevelColor(Level level);
    static std::string CenterText(const std::string& text, size_t width);
    static void PrintLine(const std::string& line);
};

}  // namespace core
