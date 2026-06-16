/**
 * @file ThreadSafeQueue.hpp
 * @brief Fila thread-safe baseada em buffer circular implementado manualmente.
 *
 * @details Implementa o padrão Produtor/Consumidor usando um ring buffer de capacidade
 * fixa. A sincronização é feita com mutex e variáveis de condição POSIX (via std::).
 * Os corpos dos métodos ficam em ThreadSafeQueue.cpp via explicit template instantiation.
 */
#pragma once
#include <condition_variable>
#include <cstddef>
#include <mutex>

namespace core {

/**
 * @class ThreadSafeQueue
 * @brief Fila sincronizada com ring buffer manual (sem std::queue ou std::deque).
 *
 * @details Internamente usa um array alocado dinamicamente com head/tail/count para
 * implementar o buffer circular. A capacidade é definida na construção e é fixa.
 *
 * @tparam T Tipo do dado armazenado.
 */
template <typename T>
class ThreadSafeQueue {
   private:
    T* data_;
    size_t head_;
    size_t tail_;
    size_t count_;
    const size_t capacity_;
    bool closed_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;

   public:
    /**
     * @brief Constrói a fila alocando o ring buffer interno.
     * @param capacity Número máximo de elementos. Padrão: 100.
     */
    explicit ThreadSafeQueue(size_t capacity = 100);

    /** @brief Destrói a fila e libera o buffer alocado. */
    ~ThreadSafeQueue();

    // Não copiável nem movível — mutex e ponteiro bruto tornam isso inseguro.
    ThreadSafeQueue(const ThreadSafeQueue&) = delete;
    ThreadSafeQueue& operator=(const ThreadSafeQueue&) = delete;

    /**
     * @brief Insere um item no buffer. Bloqueia se estiver cheio.
     * @return true se inserido; false se a fila foi fechada.
     */
    bool push(const T& item);

    /**
     * @brief Remove o item mais antigo. Bloqueia se estiver vazio.
     * @param item Referência que recebe o valor removido.
     * @return true se removido; false se a fila foi fechada e está vazia.
     */
    bool pop(T& item);

    /**
     * @brief Tenta remover sem bloquear.
     * @param item Referência que recebe o valor removido.
     * @return true se havia item; false se vazio.
     */
    bool tryPop(T& item);

    /** @brief Fecha a fila e libera todas as threads bloqueadas. */
    void close();

    /** @brief Retorna true se o buffer não contém nenhum elemento. */
    bool empty() const;

    /** @brief Retorna true se a fila foi fechada. */
    bool isClosed() const;
};

}  // namespace core
