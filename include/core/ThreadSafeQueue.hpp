/**
 * @file ThreadSafeQueue.hpp
 * @brief Implementação de uma fila thread-safe genérica.
 */
#pragma once
#include <condition_variable>
#include <mutex>
#include <queue>

namespace core {

/**
 * @class ThreadSafeQueue
 * @brief Fila sincronizada baseada em mutexes e variáveis de condição.
 *
 * @details Previne race conditions e deadlocks no modelo Produtor/Consumidor.
 * @tparam T Tipo de dado que será armazenado na fila.
 */
template <typename T>
class ThreadSafeQueue {
   private:
    std::queue<T> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    const size_t max_capacity_;
    bool closed_{false};

   public:
    /**
     * @brief Construtor da fila segura.
     * @param capacity Capacidade máxima da fila antes de bloquear o produtor. Padrão: 100.
     */
    explicit ThreadSafeQueue(size_t capacity = 100) : max_capacity_(capacity) {}

    /**
     * @brief Insere um item na fila de forma segura.
     *
     * @details Se a fila estiver cheia, a thread produtora é suspensa até haver espaço.
     * @param item O elemento a ser inserido.
     * @return true se inseriu o item; false se a fila foi fechada.
     */
    bool push(const T& item) {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this]() { return closed_ || queue_.size() < max_capacity_; });

        if (closed_) {
            return false;
        }

        queue_.push(item);
        lock.unlock();
        cv_.notify_one();
        return true;
    }

    /**
     * @brief Remove o item mais antigo da fila, aguardando se necessário.
     *
     * @details Se a fila estiver vazia, a thread consumidora é suspensa até chegar um novo dado
     * ou até a fila ser fechada.
     * @param item Referência que receberá o item removido.
     * @return true se removeu um item; false se a fila foi fechada e ficou vazia.
     */
    bool pop(T& item) {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this]() { return closed_ || !queue_.empty(); });

        if (queue_.empty()) {
            return false;
        }

        item = queue_.front();
        queue_.pop();
        lock.unlock();
        cv_.notify_all();
        return true;
    }

    /**
     * @brief Tenta remover um item da fila sem bloquear.
     * @param item Referência que receberá o item removido.
     * @return true se removeu um item; false se a fila estava vazia.
     */
    bool tryPop(T& item) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (queue_.empty()) {
            return false;
        }

        item = queue_.front();
        queue_.pop();
        cv_.notify_all();
        return true;
    }

    /**
     * @brief Fecha a fila e libera todas as threads bloqueadas.
     */
    void close() {
        std::lock_guard<std::mutex> lock(mutex_);
        closed_ = true;
        cv_.notify_all();
    }

    /**
     * @brief Verifica se a fila está vazia (de forma segura).
     * @return true se vazia, false caso contrário.
     */
    bool empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.empty();
    }

    /**
     * @brief Verifica se a fila foi fechada.
     * @return true se fechada, false caso contrário.
     */
    bool isClosed() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return closed_;
    }
};

}  // namespace core