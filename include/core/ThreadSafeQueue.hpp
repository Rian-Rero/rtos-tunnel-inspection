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
 * * Previne race conditions e deadlocks no modelo Produtor/Consumidor.
 * @tparam T Tipo de dado que será armazenado na fila.
 */
template <typename T>
class ThreadSafeQueue {
   private:
    std::queue<T> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    const size_t max_capacity_;

   public:
    /**
     * @brief Construtor da fila segura.
     * @param capacity Capacidade máxima da fila antes de bloquear o produtor. Padrão: 100.
     */
    explicit ThreadSafeQueue(size_t capacity = 100) : max_capacity_(capacity) {}

    /**
     * @brief Insere um item na fila de forma segura.
     * Se a fila estiver cheia, a thread produtora é suspensa até haver espaço.
     * @param item O elemento a ser inserido.
     */
    void push(const T& item) {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this]() { return queue_.size() < max_capacity_; });

        queue_.push(item);
        lock.unlock();
        cv_.notify_one();
    }

    /**
     * @brief Remove e retorna o item mais antigo da fila.
     * Se a fila estiver vazia, a thread consumidora é suspensa até chegar um novo dado.
     * @return O elemento removido da fila.
     */
    T pop() {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this]() { return !queue_.empty(); });

        T item = queue_.front();
        queue_.pop();
        lock.unlock();
        cv_.notify_all();

        return item;
    }

    /**
     * @brief Verifica se a fila está vazia (de forma segura).
     * @return true se vazia, false caso contrário.
     */
    bool empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.empty();
    }
};

}  // namespace core