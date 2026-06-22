# Janelas responsivas do operador

## Objetivo

Exibir a GUI de operação e o simulador lado a lado, sem sobreposição, mantendo os três painéis atuais da GUI (Comandos, Telemetria e Pré-visualização). Nenhum botão ou texto de telemetria deve ultrapassar seu contêiner. Ao trocar de AUTO para MANUAL, o setpoint manual deve começar com o mesmo valor que estava ativo no modo automático.

## Layout

- Cada aplicação calcula sua geometria a partir da área disponível da tela.
- A GUI do operador ocupa a metade esquerda e o simulador ocupa a metade direita.
- Margens externas e um pequeno espaço entre as janelas evitam contato e sobreposição.
- A GUI mantém os três painéis atuais. Suas colunas distribuem a largura disponível sem exigir a largura mínima antiga de 1080 px.
- Grupos de botões usam `grid` e células expansíveis. Os botões de modo são reorganizados verticalmente quando o painel fica estreito; os direcionais continuam em uma linha e podem encolher uniformemente.
- Rótulos descritivos e valores de telemetria quebram linha de acordo com a largura efetiva do painel.

## Preservação do setpoint

- O modelo Python passa a ler `speed_setpoint` da mensagem `telemetry/robot` já publicada pelo núcleo C++.
- Enquanto o robô está em AUTO, o painel de comandos memoriza e apresenta o módulo desse setpoint sem republicá-lo.
- Ao selecionar MANUAL, a GUI publica primeiro o setpoint e a direção memorizados e depois o comando de mudança de modo. Assim, o movimento mantém o mesmo estado instantâneo observado no modo AUTO.
- Na ausência de telemetria automática válida, aplica-se o setpoint manual já mostrado no controle, limitado ao intervalo configurado de 0 a 100%.

## Componentes afetados

- `src/gui/app.py`: geometria da janela, distribuição das colunas, sincronização entre telemetria e comandos.
- `src/gui/panels.py`: layout adaptável dos controles e sincronização silenciosa do setpoint.
- `src/simulator/app.py`: geometria da janela Pygame na metade direita.
- `src/models.py`: campo e leitura do setpoint recebido por telemetria.

## Validação

- Testar os cálculos de geometria em resoluções usuais, incluindo 1366×768 e 1920×1080.
- Verificar que os limites das duas janelas não se intersectam.
- Instanciar a GUI e conferir que botões e textos permanecem dentro de seus painéis na menor geometria suportada.
- Simular telemetria AUTO com diferentes setpoints e confirmar que AUTO → MANUAL publica o mesmo valor, sem publicação causada apenas pela atualização visual do slider.
- Preservar a alteração local já existente que exibe somente o ícone no botão STOP.
