cmake_minimum_required(VERSION 3.14)
project(rtos_tunnel_inspection VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Adicionando as flags de compilação que você tinha no Makefile
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")

# Inclui os cabeçalhos
include_directories(include)

# Encontra todos os arquivos fonte
file(GLOB_RECURSE SOURCES "src/*.cpp")

# Cria o executável principal
add_executable(atr_inspection ${SOURCES})

# Adiciona a biblioteca de threads do sistema operacional
find_package(Threads REQUIRED)
target_link_libraries(atr_inspection Threads::Threads)

# ==========================================
# COMANDOS DE EXECUÇÃO E DOCUMENTAÇÃO
# ==========================================

# Equivalente ao 'make run'
add_custom_target(run
    COMMAND chmod +x ${CMAKE_SOURCE_DIR}/run.sh
    COMMAND ${CMAKE_SOURCE_DIR}/run.sh
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Iniciando o ecossistema completo..."
)

# Equivalente ao 'make part1'
add_custom_target(part1
    COMMAND chmod +x ${CMAKE_SOURCE_DIR}/part1.sh
    COMMAND ${CMAKE_SOURCE_DIR}/part1.sh
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Iniciando o ecossistema da Parte 1..."
)

# Equivalente ao 'make docs'
add_custom_target(docs
    COMMAND echo "========================================="
    COMMAND echo "  Gerando Documentação C++ (Doxygen)...  "
    COMMAND echo "========================================="
    COMMAND doxygen Doxyfile
    COMMAND echo "Documentação C++ gerada na pasta 'html/'."
    COMMAND echo ""
    COMMAND echo "========================================="
    COMMAND echo "  Gerando Documentação Python (MkDocs)..."
    COMMAND echo "========================================="
    COMMAND mkdocs build
    COMMAND echo "Documentação Python gerada na pasta 'site/'."
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)

# Equivalente ao 'make docs-serve'
add_custom_target(docs-serve
    COMMAND mkdocs serve
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Subindo servidor local do MkDocs..."
)