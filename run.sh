#!/bin/bash

echo "====================================================="
echo "      Inicializando Ecossistema Completo ATR         "
echo "====================================================="

# Passo 1: Compilar o código C++
echo "[1/2] Compilando o código-fonte C++..."
cd build && make

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Erro na compilação. Corrija os erros acima e tente novamente."
    exit 1
fi

echo "✅ Compilação concluída com sucesso."
echo ""

# Passo 2: Iniciar os serviços
echo "[2/2] Iniciando o Cérebro do Robô..."
echo "Pressione CTRL+C a qualquer momento para encerrar tudo."
echo "-----------------------------------------------------"

./atr_inspection