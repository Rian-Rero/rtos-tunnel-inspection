/**
 * @file ThreadSafeQueue.cpp
 * @brief Implementação do buffer circular thread-safe feito manualmente.
 *
 * @details Ring buffer com head/tail/count e aritmética modular — sem std::queue.
 * A técnica de explicit template instantiation permite manter as definições
 * aqui no .cpp em vez de expô-las no header, preservando o encapsulamento.
 */
#include "core/ThreadSafeQueue.hpp"

#include "core/DataTypes.hpp"

namespace core {

// ─── Construtor / Destrutor ──────────────────────────────────────────────────

template <typename T>
ThreadSafeQueue<T>::ThreadSafeQueue(size_t capacity)
    : data_(new T[capacity]), head_(0), tail_(0), count_(0), capacity_(capacity), closed_(false) {}

template <typename T>
ThreadSafeQueue<T>::~ThreadSafeQueue() {
    delete[] data_;
}

// ─── push ────────────────────────────────────────────────────────────────────

template <typename T>
bool ThreadSafeQueue<T>::push(const T& item) {
    std::unique_lock<std::mutex> lock(mutex_);

    // Produtor dorme enquanto o buffer estiver cheio (count_ == capacity_).
    cv_.wait(lock, [this]() { return closed_ || count_ < capacity_; });

    if (closed_) {
        return false;
    }

    // Escreve na posição head_ e avança head_ circularmente.
    data_[head_] = item;
    head_ = (head_ + 1) % capacity_;
    count_++;

    lock.unlock();
    cv_.notify_one();
    return true;
}

// ─── pop ─────────────────────────────────────────────────────────────────────

template <typename T>
bool ThreadSafeQueue<T>::pop(T& item) {
    std::unique_lock<std::mutex> lock(mutex_);

    // Consumidor dorme enquanto o buffer estiver vazio.
    cv_.wait(lock, [this]() { return closed_ || count_ > 0; });

    if (count_ == 0) {
        return false;
    }

    // Lê da posição tail_ e avança tail_ circularmente.
    item = data_[tail_];
    tail_ = (tail_ + 1) % capacity_;
    count_--;

    lock.unlock();
    cv_.notify_all();
    return true;
}

// ─── tryPop ──────────────────────────────────────────────────────────────────

template <typename T>
bool ThreadSafeQueue<T>::tryPop(T& item) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (count_ == 0) {
        return false;
    }

    item = data_[tail_];
    tail_ = (tail_ + 1) % capacity_;
    count_--;

    cv_.notify_all();
    return true;
}

// ─── close / empty / isClosed ────────────────────────────────────────────────

template <typename T>
void ThreadSafeQueue<T>::close() {
    std::lock_guard<std::mutex> lock(mutex_);
    closed_ = true;
    cv_.notify_all();
}

template <typename T>
bool ThreadSafeQueue<T>::empty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return count_ == 0;
}

template <typename T>
bool ThreadSafeQueue<T>::isClosed() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return closed_;
}

// ─── Explicit template instantiation ─────────────────────────────────────────
//
// Informa ao linker quais especializações compilar a partir deste .cpp.
// Sem isso, o linker não encontraria os símbolos ao usar a classe nos outros
// arquivos — é o preço de separar a implementação do template do header.

template class ThreadSafeQueue<NavigationSetpoint>;
template class ThreadSafeQueue<SurfaceData>;

}  // namespace core
