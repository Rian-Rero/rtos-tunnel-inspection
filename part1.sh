#!/bin/bash

echo "====================================================="
echo "  Inicializando Sistema ATR - Apenas Etapa 1 (C++)   "
echo "====================================================="

# Passo 1: Compilar o código C++
echo "[1/2] Compilando o código-fonte C++..."

# Entra na pasta build gerada pelo CMake e compila
cd build && make

# Verifica se a compilação foi bem sucedida
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Erro na compilação. Corrija os erros acima e tente novamente."
    exit 1
fi

echo "✅ Compilação concluída com sucesso."
echo ""

# Passo 2: Iniciar o Núcleo C++
echo "[2/2] Iniciando o Cérebro do Robô..."
echo "Pressione CTRL+C a qualquer momento para encerrar."
echo "-----------------------------------------------------"

# Executa o programa compilado pelo CMake
./atr_inspection