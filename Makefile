# Makefile
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -Iinclude -pthread -O2

SRC_DIR = src
OBJ_DIR = build
BIN_DIR = bin

TARGET = $(BIN_DIR)/inspection_robot

# Encontra todos os arquivos .cpp recursivamente
SOURCES = $(shell find $(SRC_DIR) -name '*.cpp')
OBJECTS = $(patsubst $(SRC_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(SOURCES))

all: $(TARGET)

$(TARGET): $(OBJECTS)
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS) -o $@ $^

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -rf $(OBJ_DIR) $(BIN_DIR)

.PHONY: all clean

# ==========================================
# COMANDOS DE EXECUÇÃO E DOCUMENTAÇÃO
# ==========================================

# Comando para rodar o projeto todo
run: all
	@echo "Iniciando o ecossistema completo..."
	@chmod +x run.sh
	./run.sh

# Comando para gerar ambas as documentações (C++ e Python)
docs:
	@echo "========================================="
	@echo "  Gerando Documentação C++ (Doxygen)...  "
	@echo "========================================="
	doxygen Doxyfile
	@echo "Documentação C++ gerada na pasta 'html/'."
	@echo ""
	@echo "========================================="
	@echo "  Gerando Documentação Python (MkDocs)..."
	@echo "========================================="
	mkdocs build
	@echo "Documentação Python gerada na pasta 'site/'."

# Comando para subir o servidor da documentação Python ao vivo
docs-serve:
	@echo "Subindo servidor local do MkDocs..."
	mkdocs serve