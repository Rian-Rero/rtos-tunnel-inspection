"""Paleta de cores do ATR, fonte única para Pygame (tuplas RGB)
e Tkinter (strings hexadecimais).

Todos os módulos de renderização importam daqui; constantes de cor não
devem aparecer no código da aplicação.
"""

from __future__ import annotations

from typing import NamedTuple

__all__ = ["RGB", "Palette", "hex_palette"]


class RGB(NamedTuple):
    """Cor RGB imutável compartilhada pelos renderizadores."""

    ## @var r
    # Canal vermelho.
    r: int  ##< Canal vermelho.
    ## @var g
    # Canal verde.
    g: int  ##< Canal verde.
    ## @var b
    # Canal azul.
    b: int  ##< Canal azul.

    def hex(self) -> str:
        """Converte a cor para string hexadecimal compatível com Tkinter."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def with_alpha(self, a: int) -> tuple[int, int, int, int]:
        """Retorna a cor com canal alfa anexado."""
        return (self.r, self.g, self.b, a)


class Palette:
    """Tuplas RGB prontas para Pygame usadas no robô ATR."""

    # ── Esteiras ─────────────────────────────────────────────────────────────
    TRACK_FILL = RGB(26, 31, 39)  ##< Preenchimento das esteiras.
    TRACK_OUTLINE = RGB(55, 65, 76)  ##< Contorno das esteiras.
    TRACK_TREAD = RGB(17, 21, 27)  ##< Frisos móveis das esteiras.
    TRACK_HIGHLIGHT = RGB(70, 82, 96)  ##< Realce superior das esteiras.
    SPROCKET_FILL = RGB(45, 52, 62)  ##< Preenchimento das rodas motrizes.
    SPROCKET_OUTLINE = RGB(88, 100, 114)  ##< Contorno das rodas motrizes.
    SPROCKET_SPOKE = RGB(106, 120, 136)  ##< Raios das rodas motrizes.
    SPROCKET_HUB = RGB(65, 75, 88)  ##< Cubo central das rodas motrizes.
    ROAD_WHEEL_FILL = RGB(38, 45, 54)  ##< Preenchimento das rodas de apoio.
    ROAD_WHEEL_OUTLINE = RGB(72, 84, 98)  ##< Contorno das rodas de apoio.
    ROAD_WHEEL_HUB = RGB(52, 62, 74)  ##< Cubo das rodas de apoio.

    # ── Corpo ────────────────────────────────────────────────────────────────
    BODY_FILL = RGB(65, 84, 98)  ##< Preenchimento da carroceria.
    BODY_OUTLINE = RGB(106, 128, 146)  ##< Contorno da carroceria.
    BODY_PANEL = RGB(46, 63, 76)  ##< Linha de painel da carroceria.

    # ── Caixa de equipamentos ────────────────────────────────────────────────
    EQ_BOX_FILL = RGB(52, 68, 82)  ##< Preenchimento da caixa de equipamentos.
    EQ_BOX_OUTLINE = RGB(88, 108, 124)  ##< Contorno da caixa de equipamentos.
    EQ_BOX_VENT = RGB(32, 48, 60)  ##< Aberturas de ventilação.

    # ── Antena ───────────────────────────────────────────────────────────────
    ANTENNA_STEM = RGB(168, 186, 204)  ##< Haste da antena.
    ANTENNA_TIP = RGB(200, 218, 236)  ##< Ponta da antena.
    ANTENNA_GLOW = RGB(96, 170, 255)  ##< Brilho da antena.

    # ── Cúpula do LiDAR ──────────────────────────────────────────────────────
    LIDAR_MOUNT_FILL = RGB(48, 62, 76)  ##< Base do suporte do LIDAR.
    LIDAR_MOUNT_OUTLINE = RGB(84, 102, 118)  ##< Contorno do suporte do LIDAR.
    LIDAR_SHELL = RGB(38, 50, 63)  ##< Carcaça do LIDAR.
    LIDAR_SHELL_OUTLINE = RGB(70, 86, 102)  ##< Contorno da carcaça do LIDAR.
    LIDAR_LENS = RGB(18, 94, 168)  ##< Lente do LIDAR.
    LIDAR_LENS_RING = RGB(50, 154, 248)  ##< Aro da lente do LIDAR.
    LIDAR_SHINE_OUTER = RGB(155, 210, 255)  ##< Brilho externo da lente.
    LIDAR_SHINE_INNER = RGB(215, 240, 255)  ##< Brilho interno da lente.

    # ── Braço da câmera ──────────────────────────────────────────────────────
    ARM_STEEL = RGB(128, 146, 162)  ##< Metal principal do braço da câmera.
    ARM_HIGHLIGHT = RGB(158, 175, 192)  ##< Realce do braço da câmera.
    ARM_JOINT = RGB(76, 92, 108)  ##< Junta do braço da câmera.
    ARM_JOINT_OUTLINE = RGB(124, 142, 160)  ##< Contorno da junta da câmera.
    CAM_BODY = RGB(20, 26, 34)  ##< Corpo da câmera.
    CAM_BODY_OUTLINE = RGB(104, 120, 138)  ##< Contorno do corpo da câmera.
    CAM_LENS = RGB(28, 100, 178)  ##< Lente da câmera.
    CAM_LENS_RING = RGB(52, 150, 238)  ##< Aro da lente da câmera.
    CAM_SHINE = RGB(170, 212, 252)  ##< Brilho da lente da câmera.
    LED_ACTIVE = RGB(248, 113, 113)  ##< LED quando a inspeção está ativa.
    LED_IDLE = RGB(74, 222, 128)  ##< LED quando a câmera está ociosa.

    # ── Indicador de inclinação ──────────────────────────────────────────────
    SLOPE_UP = RGB(250, 204, 21)  ##< Cor usada para subida.
    SLOPE_DOWN = RGB(96, 165, 250)  ##< Cor usada para descida.
    SLOPE_FLAT = RGB(148, 163, 184)  ##< Cor usada para trecho plano.


def hex_palette() -> dict[str, str]:
    """Retorna as entradas da Palette como {nome: cor_hex} (para Tkinter)."""
    return {
        name: value.hex()
        for name, value in vars(Palette).items()
        if isinstance(value, RGB)
    }
