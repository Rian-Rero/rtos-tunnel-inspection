/**
 * @file TerminalPrinter.hpp
 * @brief Utilitario para impressao padronizada e estilizada no terminal.
 */
#pragma once

#include <string>

namespace core {

/**
 * @class TerminalPrinter
 * @brief Centraliza logs e banners com padrao visual consistente.
 *
 * Fornece niveis de severidade, carimbo de tempo e blocos de destaque
 * para facilitar a leitura durante a execucao em tempo real.
 */
class TerminalPrinter {
   public:
    /**
     * @brief Niveis de severidade para logs.
     */
    enum class Level {
        Info,    /**< Informacao geral */
        Success, /**< Operacao concluida com sucesso */
        Warning, /**< Aviso de atencao */
        Error,   /**< Erro critico */
        Debug    /**< Informacoes de depuracao */
    };

    /**
     * @brief Imprime um banner de abertura com titulo e subtitulo opcionais.
     * @param title Texto principal do banner.
     * @param subtitle Texto secundario abaixo do titulo (opcional).
     */
    static void Banner(const std::string& title, const std::string& subtitle = "");

    /**
     * @brief Imprime um divisor de secao com titulo centralizado.
     * @param title Texto da secao.
     */
    static void Section(const std::string& title);

    /**
     * @brief Imprime um log formatado com nivel, escopo e mensagem.
     * @param level Nivel de severidade.
     * @param scope Nome curto do subsistema (ex: "Camera", "Coletor").
     * @param message Conteudo da mensagem.
     */
    static void Log(Level level, const std::string& scope, const std::string& message);

    /**
     * @brief Imprime um log formatado sem escopo.
     * @param level Nivel de severidade.
     * @param message Conteudo da mensagem.
     */
    static void Log(Level level, const std::string& message);

    /**
     * @brief Imprime uma linha simples sem decoracao.
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
