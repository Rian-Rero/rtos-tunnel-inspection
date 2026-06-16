"""Renderizador da cena Pygame: tudo exceto o modelo do robô.

*TunnelScene* recebe um retrato *SceneState* por quadro e desenha:
  - caverna natural: terra compactada, rocha e escuridão profunda
  - perfil do teto com estratos geológicos reais e textura rochosa
  - anomalias visuais: buraco (cavidade escura) e saliência (volume 3-D)
  - geologia do piso: terra batida e pedras espalhadas
  - efeito de tocha: zona iluminada central, escuridão nas bordas
  - sobreposição de varredura de inclinação
  - marcadores de anomalia
  - régua de distância
  - painel do monitor da câmera
  - névoa de áreas ainda não mapeadas
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from models import AnomalyMark, InspectionState
from .terrain import ViewTransform, slope_label, slope_color_rgb, local_imu

__all__ = ["SceneState", "TunnelScene"]


@dataclass
class SceneState:
    """Retrato do estado do simulador necessário para renderizar um quadro."""

    ## Posição suavizada do robô usada pela câmera virtual.
    visual_pos_x: float
    ## Posição máxima já revelada pelo mapeamento do túnel.
    reveal_pos_x: float
    ## Inclinação atual da IMU, em graus.
    imu: float
    ## Última leitura do LIDAR, em metros.
    lidar: float
    ## Histórico bruto de telemetria usado para desenhar o perfil.
    robot_history: list[dict] = field(default_factory=list)
    ## Marcadores de anomalia já detectados no perfil.
    anomaly_marks: list[AnomalyMark] = field(default_factory=list)
    ## Estado atual da inspeção visual.
    inspection: InspectionState = field(default_factory=InspectionState)


class TunnelScene:
    """Renderizador Pygame sem estado para o ambiente do túnel natural."""

    # ── Paleta geológica ─────────────────────────────────────────────────────
    _C_CAVE_AIR = (3, 2, 1)  ##< Cor do ar escuro da caverna.
    _C_ROCK_DEEP = (28, 16, 6)  ##< Rocha profunda pouco iluminada.
    _C_ROCK_BODY = (44, 28, 12)  ##< Massa principal da rocha.
    _C_ROCK_MID = (56, 36, 16)  ##< Tom intermediário dos estratos.
    _C_EARTH_DARK = (70, 46, 22)  ##< Terra compactada escura.
    _C_FACE_BASE = (76, 56, 34)  ##< Face inferior básica do teto.
    _C_FACE_LIT = (108, 80, 48)  ##< Face inferior iluminada.
    _C_CRACK = (20, 11, 5)  ##< Fissuras escuras na rocha.
    _C_OCHRE = (105, 76, 38)  ##< Tom ocre usado em detalhes geológicos.

    # ── público ──────────────────────────────────────────────────────────────

    def draw_background(self, screen: pygame.Surface) -> None:
        """Desenha o fundo rochoso e a massa escura da caverna."""
        width, height = screen.get_size()

        # Escuridão absoluta da caverna
        screen.fill(self._C_CAVE_AIR)

        # ── Massa rochosa superior (y 0–78): estratos geológicos ─────────────
        upper_strata = [
            (0, 13, (26, 15, 6)),
            (13, 25, (40, 24, 10)),
            (25, 37, (52, 33, 15)),
            (37, 50, (46, 29, 13)),
            (50, 62, (38, 24, 10)),
            (62, 78, (28, 17, 7)),
        ]
        for y0, y1, col in upper_strata:
            pygame.draw.rect(screen, col, (0, y0, width, y1 - y0))

        # Textura rochosa na massa superior: nódulos, fissuras, pedras expostas
        top_srf = pygame.Surface((width, 80), pygame.SRCALPHA)
        n_samples = max(1, width // 5)
        for i in range(n_samples * 6):
            a = ((i * 1664525 + 1013904223) >> 4) & 0xFF
            b = ((i * 22695477 + 12345678) >> 5) & 0xFF
            c = ((i * 134775813 + 1) >> 6) & 0xFF
            px = (a * 4 + b * 3 + i * 11) % width
            py = 3 + (c % 68)
            kind = i % 6
            if kind < 3:  # nódulo rochoso
                pr = 1 + (b % 4)
                col = (46 + a % 32, 30 + b % 22, 12 + c % 14, 75 + a % 95)
                pygame.draw.ellipse(
                    top_srf, col, (px - pr, py - pr // 2, pr * 2, max(1, pr))
                )
            elif kind == 3:  # fissura
                x2 = px + (b % 32) - 16
                y2 = py + (c % 16) - 5
                pygame.draw.line(
                    top_srf, (14, 8, 3, 115 + b % 75), (px, py), (x2, y2), 1
                )
            elif kind == 4:  # pedra exposta de granito / sílex
                pr = 2 + (b % 5)
                lum = 58 + c % 35
                pygame.draw.ellipse(
                    top_srf,
                    (lum, lum - 12, lum - 26, 88 + a % 70),
                    (px - pr, py - pr // 2, pr * 2, max(1, pr)),
                )
            else:  # mancha de argila avermelhada
                pr = 3 + (a % 6)
                pygame.draw.ellipse(
                    top_srf,
                    (80 + b % 28, 40 + c % 18, 18 + a % 10, 55 + b % 55),
                    (px - pr, py - pr // 2, pr * 2, max(1, pr)),
                )
        screen.blit(top_srf, (0, 0))

        # Sutil separação inferior da massa (onde o teto começa)
        pygame.draw.rect(screen, (20, 12, 5), (0, 75, width, 3))

        # Interior do túnel: ar da caverna, quase preto com leve calor
        pygame.draw.rect(screen, (5, 3, 2), (0, 78, width, height - 154))

    def draw_overlay(self, screen: pygame.Surface) -> None:
        """Aplica escurecimento periférico e brilho central de tocha."""
        width, height = screen.get_size()

        # ── Escuridão da caverna com efeito de tocha do robô ─────────────────
        cx = width // 2
        cy = height - 195  # posição aproximada do robô / piso

        dark = pygame.Surface((width, height), pygame.SRCALPHA)
        dark.fill((2, 1, 0, 220))

        # Gradiente radial: transparente no centro → opaco nas bordas
        max_r = int(min(width * 0.52, height * 0.82))
        step = 3
        for r in range(max_r, 0, -step):
            t = r / max_r
            alpha = int(216 * (t**1.60))
            pygame.draw.circle(dark, (2, 1, 0, alpha), (cx, cy), r)

        screen.blit(dark, (0, 0))

        # Reflexo âmbar da tocha (calor no núcleo iluminado)
        glow = pygame.Surface((width, height), pygame.SRCALPHA)
        gr = max_r // 4
        for r in range(gr, 0, -3):
            t = 1.0 - r / gr
            alpha = int(24 * (t**2.4))
            pygame.draw.circle(glow, (188, 122, 44, alpha), (cx, cy + 28), r)
        screen.blit(glow, (0, 0))

    def draw_tunnel_profile(
        self, screen: pygame.Surface, state: SceneState, view: ViewTransform
    ) -> None:
        """Desenha teto, piso, régua e sobreposições de mapeamento do túnel."""
        width, height = screen.get_size()
        floor_fn = view.make_floor_fn(height, state.visual_pos_x)
        roof_mid_y = 178

        history = state.robot_history
        if not history:
            font = pygame.font.SysFont("arial", 22, bold=True)
            screen.blit(
                font.render(
                    "Aguardando telemetria do C++ via MQTT...", True, (226, 232, 240)
                ),
                (28, 120),
            )

        visible = [
            s
            for s in history
            if view.view_start_m
            <= float(s.get("pos_x", state.visual_pos_x))
            <= view.view_end_m
        ] or history[-1:]

        raw_pts = []
        for s in visible:
            sx = float(s.get("pos_x", state.visual_pos_x))
            lidar = float(s.get("lidar_distance_y", s.get("lidar", 2.0)))
            x = view.screen_x(sx)
            ry = roof_mid_y - (lidar - 2.0) * 82.0
            ry += math.sin(math.radians(state.imu)) * (x - width / 2) * 0.045
            raw_pts.append((x, max(86, min(height - 230, ry)), lidar))

        path_pts = []
        for i, (x, _, _) in enumerate(raw_pts):
            win = raw_pts[max(0, i - 2) : i + 3]
            path_pts.append((x, sum(p[1] for p in win) / len(win)))

        floor_top = [(x, floor_fn(x)) for x in range(-24, width + 25, 24)]

        self._draw_ceiling(screen, path_pts, view, width, height)
        self._draw_floor_terrain(
            screen, floor_top, width, height, view, floor_fn, state.visual_pos_x
        )
        self._draw_slope_scan(screen, view, state.imu)
        self._draw_distance_ruler(screen, view, floor_fn)
        self._draw_imu_gauge(screen, state.imu)
        self._draw_unmapped_overlay(screen, view, state.reveal_pos_x)

    def draw_camera_monitor(
        self,
        screen: pygame.Surface,
        insp: InspectionState,
        camera_image: pygame.Surface | None = None,
    ) -> None:
        """Desenha o monitor flutuante da câmera de inspeção."""
        width, _ = screen.get_size()
        if not insp.active and insp.result_expires_at is None:
            return

        # Fundo e borda do painel flutuante
        rect = pygame.Rect(width - 380, 84, 344, 138)
        srf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(srf, (8, 13, 23, 232), srf.get_rect(), border_radius=6)
        pygame.draw.rect(srf, (96, 165, 250, 190), srf.get_rect(), 2, border_radius=6)

        # Área exata onde a imagem da câmera será desenhada
        view_rect = pygame.Rect(20, 34, 176, 86)

        if camera_image is not None:
            scaled_image = pygame.transform.smoothscale(
                camera_image, (view_rect.width, view_rect.height)
            )

            # Realce de visão noturna: clareia artificialmente a rocha escura.
            boost = pygame.Surface(scaled_image.get_size())
            boost.fill((60, 60, 60))
            scaled_image.blit(boost, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

            if not insp.active and insp.last_type:
                box_color = (34, 197, 94)

                # Desenha o quadrado no centro da foto
                bw, bh = 80, 40
                bx = (view_rect.width - bw) // 2
                by = (view_rect.height - bh) // 2
                pygame.draw.rect(scaled_image, box_color, (bx, by, bw, bh), 2)

                # Fundo do texto da etiqueta
                pygame.draw.rect(scaled_image, box_color, (bx, by - 12, bw, 12))

                # Escreve a anomalia na etiqueta
                tiny_font = pygame.font.SysFont("arial", 9, bold=True)
                yolo_text = f"{insp.last_type} {insp.last_confidence:.2f}"
                text_surf = tiny_font.render(yolo_text, True, (0, 0, 0))
                scaled_image.blit(text_surf, (bx + 2, by - 12))

            srf.blit(scaled_image, view_rect.topleft)

            # Indicador de "REC"
            if insp.active and (pygame.time.get_ticks() % 1000 < 500):
                pygame.draw.circle(
                    srf, (239, 68, 68), (view_rect.right - 12, view_rect.top + 12), 4
                )

        else:
            # Estado inativo / sem sinal (linhas cinzas diagonais)
            pygame.draw.rect(srf, (64, 67, 73), view_rect, border_radius=4)
            for y in range(view_rect.y + 8, view_rect.bottom - 4, 13):
                pygame.draw.line(
                    srf,
                    (92, 96, 104),
                    (view_rect.x + 4, y),
                    (view_rect.right - 4, y + 8),
                    2,
                )

        # ── Textos do painel ──────────────────────────────────────────────
        label = "CAPTURANDO" if insp.active else insp.last_type.upper()
        font = pygame.font.SysFont("arial", 12, bold=True)
        small = pygame.font.SysFont("arial", 11)
        text_x = view_rect.right + 16
        text_max = rect.width - text_x - 12

        srf.blit(font.render("CÂMERA DO ROBÔ", True, (226, 232, 240)), (12, 5))
        for i, line in enumerate(self._wrap_text(label, font, text_max, 2)):
            srf.blit(font.render(line, True, (191, 219, 254)), (text_x, 30 + i * 16))
        srf.blit(
            small.render(f"conf {insp.last_confidence:.2f}", True, (148, 163, 184)),
            (text_x, 68),
        )
        srf.blit(small.render("imagem real", True, (148, 163, 184)), (text_x, 88))

        screen.blit(srf, rect)

    # ── auxiliares privados ─────────────────────────────────────────────────

    @staticmethod
    def _wrap_text(
        text: str, font: pygame.font.Font, max_width: int, max_lines: int
    ) -> list[str]:
        """Quebra textos curtos do HUD sem cortar palavras importantes."""
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
            if len(lines) == max_lines - 1:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        return lines or [text]

    def _draw_floor_terrain(
        self,
        screen,
        floor_top,
        width: int,
        height: int,
        view: ViewTransform,
        floor_fn,
        visual_pos_x: float,
    ) -> None:
        """Piso natural: terra compactada em camadas com pedras espalhadas."""

        # Camada de rocha-base profunda
        floor_poly = floor_top + [(width + 24, height), (-24, height)]
        pygame.draw.polygon(screen, (40, 23, 9), floor_poly)

        # Faixa de argila subsuperficial
        clay_bot = [(x, min(height, y + 70)) for x, y in reversed(floor_top)]
        pygame.draw.polygon(screen, (62, 38, 17), floor_top + clay_bot)

        # Crosta superficial de terra compactada
        top_bot = [(x, min(height, y + 25)) for x, y in reversed(floor_top)]
        pygame.draw.polygon(screen, (88, 56, 29), floor_top + top_bot)

        # Faixa de transição superior (terra mais clara e avermelhada)
        thin_bot = [(x, min(height, y + 8)) for x, y in reversed(floor_top)]
        pygame.draw.polygon(screen, (105, 68, 36), floor_top + thin_bot)

        # ── Pedras e fragmentos fixos no mundo ──────────────────────────────
        w_step = 0.16
        wi_start = int(view.view_start_m / w_step) - 1
        wi_end = int(view.view_end_m / w_step) + 2

        for wi in range(wi_start, wi_end):
            wx = wi * w_step
            sx = view.screen_x(wx)
            if not (-30 <= sx <= width + 30):
                continue
            sy = floor_fn(sx)

            a = ((wi * 1664525 + 1013904223) >> 4) & 0xFF
            b = ((wi * 22695477 + 12345678) >> 5) & 0xFF
            c = ((wi * 134775813 + 1) >> 6) & 0xFF

            # Fragmento fino na superfície
            px = sx + (a % 36) - 18
            py = sy + 2 + (b % 5)
            pw = 2 + (c % 4)
            ph = max(1, pw - 1)
            pygame.draw.ellipse(
                screen,
                (72 + a % 36, 48 + b % 28, 28 + c % 18),
                (px - pw, py - ph, pw * 2, ph * 2),
            )

            # Pedra média, a cada ~3 posições
            if a % 3 == 0:
                rx = sx + (b % 46) - 23
                ry = sy + 4 + (c % 8)
                rw = 6 + (a % 11)
                rh = 4 + (b % 5)
                # Variação de cor da pedra (cinza, marrom, ocre)
                tone = (65 + c % 26, 50 + a % 20, 32 + b % 14)
                pygame.draw.ellipse(screen, tone, (rx - rw // 2, ry - rh // 2, rw, rh))
                # Sombra pequena
                pygame.draw.line(
                    screen,
                    (28, 16, 6),
                    (rx - rw // 2, ry + rh // 2),
                    (rx + rw // 2, ry + rh // 2),
                    1,
                )

            # Pedra grande rara (sedimento)
            if c % 9 == 0:
                bx = sx + (a % 50) - 25
                by = sy + 6 + (b % 6)
                bw = 12 + (b % 14)
                bh = 7 + (c % 6)
                btone = (58 + a % 22, 44 + b % 16, 28 + c % 10)
                pygame.draw.ellipse(screen, btone, (bx - bw // 2, by - bh // 2, bw, bh))
                pygame.draw.line(
                    screen,
                    (22, 12, 5),
                    (bx - bw // 2, by + bh // 2),
                    (bx + bw // 2, by + bh // 2),
                    1,
                )

            # Fissura superficial
            if c % 11 == 0:
                cx1, cy1 = sx + (a % 24) - 12, sy
                cx2, cy2 = cx1 + (b % 16) - 8, sy + 3 + (c % 4)
                pygame.draw.line(screen, (30, 16, 6), (cx1, cy1), (cx2, cy2), 1)

        # Borda superior do piso: limite nítido com sombra
        if len(floor_top) >= 2:
            pygame.draw.lines(screen, (140, 92, 50), False, floor_top, 4)
            shadow = [(x, y + 10) for x, y in floor_top]
            pygame.draw.lines(screen, (28, 14, 5), False, shadow, 2)

    def _draw_slope_scan(self, screen, view: ViewTransform, imu: float):
        """Desenha indicadores locais de subida e descida sobre o piso."""
        width, height = screen.get_size()
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        font = pygame.font.SysFont("arial", 12, bold=True)
        last_label, cooldown_x = None, -999
        for x in range(24, width - 92, 52):
            wx = view.world_x(x)
            angle = local_imu(wx)
            lbl = slope_label(angle)
            if lbl == "PLANO":
                continue
            color = slope_color_rgb(angle)
            y = view.floor_y(height, x, 0.0)
            nx, ny = x + 42, view.floor_y(height, x + 42, 0.0)
            pygame.draw.line(layer, (*color, 155), (x, y - 17), (nx, ny - 17), 4)
            tip = (nx, ny - 17)
            pygame.draw.polygon(
                layer,
                (*color, 155),
                [tip, (tip[0] - 9, tip[1] - 5), (tip[0] - 9, tip[1] + 5)],
            )
            if lbl != last_label and x - cooldown_x > 150:
                layer.blit(font.render(lbl, True, color), (x + 2, y - 42))
                cooldown_x, last_label = x, lbl
        screen.blit(layer, (0, 0))

    def _draw_anomaly_marks(
        self, screen, state: SceneState, view: ViewTransform, roof_mid_y: int
    ):
        """Desenha rótulos visíveis das anomalias já detectadas."""
        height = screen.get_size()[1]
        width = screen.get_size()[0]
        font = pygame.font.SysFont("arial", 13, bold=True)

        visible: list[tuple[int, int, AnomalyMark]] = []
        for mark in state.anomaly_marks:
            if not (view.view_start_m <= mark.pos_x <= view.view_end_m):
                continue
            x = view.screen_x(mark.pos_x)
            y = roof_mid_y - (mark.lidar - 2.0) * 82.0
            y += math.sin(math.radians(state.imu)) * (x - width / 2) * 0.045
            y = max(86, min(height - 230, y))
            visible.append((int(x), int(y), mark))

        last_x_by_kind: dict[str, int] = {}
        for x, y, mark in visible:
            prev = last_x_by_kind.get(mark.kind, -9999)
            if abs(x - prev) < 75:
                continue
            last_x_by_kind[mark.kind] = x
            color = (96, 165, 250) if mark.kind == "Buraco" else (252, 165, 165)
            screen.blit(font.render(mark.kind, True, color), (x - 18, y - 38))

    def _draw_ceiling(
        self, screen, path_pts: list, view: ViewTransform, width: int, height: int
    ) -> None:
        """Teto rochoso natural com estratos geológicos e anomalias realistas."""
        ROOF_TOP = 78
        FACE_H = 24

        if not path_pts:
            return

        face_pts = [(int(x), int(y)) for x, y in path_pts]
        if len(face_pts) < 2:
            if face_pts:
                pygame.draw.circle(screen, self._C_FACE_BASE, face_pts[0], 5)
            return

        body_bot = [(x, y - FACE_H) for x, y in face_pts]

        # ── Corpo rochoso: massa escura do ROOF_TOP até a face ───────────────
        body_poly = [(0, ROOF_TOP)] + body_bot + [(width, ROOF_TOP)]
        pygame.draw.polygon(screen, self._C_ROCK_BODY, body_poly)

        # Núcleo mais escuro (simula espessura e profundidade da rocha)
        inner_bot = [(x, max(ROOF_TOP + 14, y - FACE_H - 8)) for x, y in face_pts]
        depth_srf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.polygon(
            depth_srf,
            (20, 11, 4, 145),
            [(0, ROOF_TOP + 8)] + inner_bot + [(width, ROOF_TOP + 8)],
        )
        screen.blit(depth_srf, (0, 0))

        # ── Estratos geológicos: faixas de cor no corpo rochoso ──────────────
        strata_defs = [
            (5, 12, (52, 33, 14, 165)),  # marrom escuro
            (17, 24, (70, 48, 21, 130)),  # marrom médio
            (29, 36, (82, 56, 25, 110)),  # marrom-ocre
            (41, 48, (62, 42, 18, 140)),  # marrom avermelhado
            (53, 58, (48, 30, 13, 120)),  # areia compactada
            (63, 69, (74, 52, 23, 95)),  # ocre quente
            (74, 79, (34, 21, 9, 130)),  # rocha densa
        ]
        strata_srf = pygame.Surface((width, height), pygame.SRCALPHA)
        for ofs_top, ofs_bot, scol in strata_defs:
            pts_top = [(x, min(y - FACE_H, ROOF_TOP + ofs_top)) for x, y in face_pts]
            pts_bot = [(x, min(y - FACE_H, ROOF_TOP + ofs_bot)) for x, y in face_pts]
            band = pts_top + list(reversed(pts_bot))
            if len(band) >= 3:
                pygame.draw.polygon(strata_srf, scol, band)
        screen.blit(strata_srf, (0, 0))

        # ── Face visível: superfície inferior exposta ao interior do túnel ───
        face_poly = body_bot + [(x, y) for x, y in reversed(face_pts)]
        pygame.draw.polygon(screen, self._C_FACE_BASE, face_poly)

        # Gradiente de luz na face: borda inferior mais iluminada pela tocha
        lit_srf = pygame.Surface((width, height), pygame.SRCALPHA)
        for i in range(len(face_pts) - 1):
            x0, y0 = face_pts[i]
            x1, y1 = face_pts[i + 1]
            pygame.draw.polygon(
                lit_srf,
                (145, 108, 64, 58),
                [(x0, y0 - 8), (x1, y1 - 8), (x1, y1), (x0, y0)],
            )
        screen.blit(lit_srf, (0, 0))

        # ── Detalhes da face: pedras embutidas, nódulos, fissuras ────────────
        w_step = 0.20
        wi_start = int(view.view_start_m / w_step) - 1
        wi_end = int(view.view_end_m / w_step) + 2

        for wi in range(wi_start, wi_end):
            wx = wi * w_step
            sx = view.screen_x(wx)
            if not (-30 <= sx <= width + 30):
                continue
            cy = self._interp_path_y(face_pts, sx)

            a = ((wi * 1664525 + 1013904223) >> 4) & 0xFF
            b = ((wi * 22695477 + 12345678) >> 5) & 0xFF
            c = ((wi * 134775813 + 1) >> 6) & 0xFF

            # Pedra exposta / nódulo na face
            px, py = sx + (a % 30) - 15, cy - 7 - (b % 9)
            pr = 2 + (c % 5)
            if a % 3 == 0:  # rocha mais dura: quartzo, sílex (mais clara)
                sc = (82 + a % 44, 64 + b % 32, 40 + c % 22)
            else:  # terra compactada
                sc = (60 + a % 24, 44 + b % 17, 24 + c % 12)
            pygame.draw.ellipse(screen, sc, (px - pr, py - pr // 2, pr * 2, max(1, pr)))
            # Sombra do nódulo
            pygame.draw.line(
                screen,
                (18, 9, 3),
                (px - pr, py + max(1, pr // 2)),
                (px + pr, py + max(1, pr // 2)),
                1,
            )

            # Fissura / rachadura (mais frequente que antes)
            if b % 4 == 0:
                dep = 5 + (a % 12)
                ex = sx + (c % 22) - 11
                ey = cy - dep
                pygame.draw.line(
                    screen, self._C_CRACK, (sx + (a % 18) - 9, cy - 2), (ex, ey), 1
                )
                if c % 3 == 0:  # fissura ramificada
                    mx = (sx + (a % 18) - 9 + ex) // 2
                    my = cy - dep // 2
                    pygame.draw.line(
                        screen,
                        (14, 7, 2),
                        (mx, my),
                        (mx + (b % 10) - 5, my - (c % 7)),
                        1,
                    )

            # Pedra embutida maior (rara — bloco de rocha)
            if c % 8 == 0:
                brx = sx + (b % 40) - 20
                bry = cy - FACE_H + 5 + (a % 10)
                brw = 6 + (b % 8)
                brh = 4 + (a % 4)
                brc = (68 + c % 32, 54 + a % 24, 34 + b % 18)
                pygame.draw.ellipse(
                    screen, brc, (brx - brw // 2, bry - brh // 2, brw, brh)
                )

        # ── Anomalias: buraco e saliência com renderização volumétrica ───────
        sorted_ys = sorted(y for _, y in face_pts)
        baseline_y = sorted_ys[len(sorted_ys) // 2]

        anom_srf = pygame.Surface((width, height), pygame.SRCALPHA)
        for i in range(len(face_pts) - 1):
            x0, y0 = face_pts[i]
            x1, y1 = face_pts[i + 1]
            mid_y = (y0 + y1) * 0.5
            # dev > 0: saliência (teto mais baixo); dev < 0: buraco (teto mais alto)
            dev = mid_y - baseline_y

            if dev < -10:
                # ── BURACO: cavidade no teto, vazio escuro com bordas rochosas ──
                t = min(1.0, (-dev - 10) / 55.0)

                # Void interior — quase completamente preto
                void_a = int(225 + t * 30)
                pygame.draw.polygon(
                    anom_srf,
                    (1, 0, 0, void_a),
                    [
                        (x0, y0 - FACE_H - 4),
                        (x1, y1 - FACE_H - 4),
                        (x1, y1 + 4),
                        (x0, y0 + 4),
                    ],
                )

                # Gradiente de profundidade: ainda mais escuro no fundo
                pygame.draw.polygon(
                    anom_srf,
                    (0, 0, 0, 245),
                    [
                        (x0, y0 - FACE_H - 4),
                        (x1, y1 - FACE_H - 4),
                        (x1, y1 - FACE_H + 6),
                        (x0, y0 - FACE_H + 6),
                    ],
                )

                # Fragmentos de rocha nas bordas da abertura
                if t > 0.22:
                    rim_a = int(115 + t * 110)
                    frag_col = (85, 62, 38, rim_a)
                    # Bordas esquerda e direita da abertura
                    pygame.draw.line(anom_srf, frag_col, (x0, y0), (x0 + 6, y0 - 9), 2)
                    pygame.draw.line(anom_srf, frag_col, (x1, y1), (x1 - 6, y1 - 9), 2)
                    # Borda irregular superior da cavidade
                    pygame.draw.line(
                        anom_srf,
                        (60, 44, 25, rim_a - 35),
                        (x0, y0 - FACE_H),
                        (x1, y1 - FACE_H),
                        2,
                    )
                    # Fragmento extra assimétrico
                    mid_x = (x0 + x1) // 2
                    mid_y_pt = (y0 + y1) // 2
                    pygame.draw.line(
                        anom_srf,
                        (72, 52, 30, int(rim_a * 0.7)),
                        (mid_x, mid_y_pt),
                        (mid_x + (int(t * 8) - 4), mid_y_pt - 7),
                        2,
                    )

                # Reflexo âmbar de umidade nas paredes do buraco
                if t > 0.48:
                    gw_a = int(16 + t * 26)
                    pygame.draw.line(
                        anom_srf, (172, 108, 36, gw_a), (x0, y0), (x1, y1), 3
                    )

            elif dev > 10:
                # ── SALIÊNCIA: protuberância rochosa projetada para o interior ──
                t = min(1.0, (dev - 10) / 40.0)

                # Corpo da saliência — mesma rocha, mais escura (menos iluminada)
                body_a = int(110 + t * 90)
                pygame.draw.polygon(
                    anom_srf,
                    (36, 22, 9, body_a),
                    [(x0, y0 - FACE_H), (x1, y1 - FACE_H), (x1, y1), (x0, y0)],
                )

                # Face inferior da saliência captando luz da tocha
                face_a = int(38 + t * 58)
                pygame.draw.polygon(
                    anom_srf,
                    (122, 92, 54, face_a),
                    [(x0, y0 - 10), (x1, y1 - 10), (x1, y1), (x0, y0)],
                )

                # Sombra lateral esquerda (contra-luz)
                sh_a = int(55 + t * 110)
                pygame.draw.polygon(
                    anom_srf,
                    (0, 0, 0, sh_a),
                    [
                        (x0, y0 - FACE_H),
                        (x0, y0),
                        (x0 + 6, y0 - 4),
                        (x0 + 6, y0 - FACE_H + 3),
                    ],
                )

                # Realce na borda inferior da protuberância (capta luz)
                hl_a = int(52 + t * 90)
                pygame.draw.line(anom_srf, (145, 110, 62, hl_a), (x0, y0), (x1, y1), 3)

                # Acúmulo de sedimento na ponta da saliência (gotícula)
                if t > 0.55:
                    drip_a = int(68 + t * 88)
                    mx = (x0 + x1) // 2
                    my = (y0 + y1) // 2
                    pygame.draw.ellipse(
                        anom_srf, (60, 42, 20, drip_a), (mx - 3, my, 7, 5)
                    )

        screen.blit(anom_srf, (0, 0))

        # ── Borda inferior da face: contorno com brilho de toque ────────────
        if len(face_pts) >= 2:
            pygame.draw.lines(screen, (102, 75, 44), False, face_pts, 3)
            pygame.draw.lines(screen, (145, 108, 62), False, face_pts, 1)
        elif face_pts:
            pygame.draw.circle(screen, (102, 75, 44), face_pts[0], 4)

    def _interp_path_y(self, face_pts: list, target_x: float) -> int:
        """Interpolação linear do y da face do teto em target_x."""
        if not face_pts:
            return 178
        if len(face_pts) == 1:
            return face_pts[0][1]
        for i in range(len(face_pts) - 1):
            x0, y0 = face_pts[i]
            x1, y1 = face_pts[i + 1]
            if x0 <= target_x <= x1 and x1 != x0:
                t = (target_x - x0) / (x1 - x0)
                return int(y0 + t * (y1 - y0))
        return face_pts[0][1] if target_x <= face_pts[0][0] else face_pts[-1][1]

    def _draw_distance_ruler(self, screen, view: ViewTransform, floor_fn):
        """Desenha marcações de distância ao longo do piso."""
        width, _ = screen.get_size()
        font = pygame.font.SysFont("arial", 13)
        for meter in range(max(0, int(view.view_start_m)), int(view.view_end_m) + 1, 3):
            x = view.screen_x(float(meter))
            if not (0 <= x <= width):
                continue
            y = floor_fn(x)
            pygame.draw.line(screen, (71, 85, 105), (x, y - 10), (x, y + 10), 1)
            screen.blit(
                font.render(f"{meter} m", True, (148, 163, 184)), (x - 16, y + 14)
            )

    def _draw_imu_gauge(self, screen, imu: float):
        """Desenha o indicador de inclinação IMU no canto superior."""
        width, _ = screen.get_size()
        lbl = slope_label(imu)
        color = slope_color_rgb(imu)
        font = pygame.font.SysFont("arial", 14, bold=True)
        screen.blit(
            font.render(f"IMU {imu:+.1f}° | {lbl}", True, color), (width - 188, 26)
        )

        gx, gy, glen = width - 230, 58, 160
        sp = max(-34, min(34, int(imu * 5.0)))
        pygame.draw.line(screen, (71, 85, 105), (gx, gy), (gx + glen, gy), 2)
        pygame.draw.line(screen, color, (gx, gy + sp), (gx + glen, gy - sp), 5)
        tip = (gx + glen, gy - sp)
        pygame.draw.polygon(
            screen, color, [tip, (tip[0] - 12, tip[1] - 7), (tip[0] - 12, tip[1] + 7)]
        )

    def _draw_unmapped_overlay(self, screen, view: ViewTransform, reveal_pos_x: float):
        """Escurece a região do túnel ainda não mapeada pelo robô."""
        width, height = screen.get_size()
        reveal_x = view.screen_x(reveal_pos_x)
        if reveal_x >= width:
            return
        srf = pygame.Surface((width, height), pygame.SRCALPHA)
        fade_w, start_x = 190, max(0, reveal_x - 70)
        for x in range(start_x, width, 6):
            p = min(1.0, max(0.0, (x - start_x) / fade_w))
            a = int(82 + p * 154)
            pygame.draw.rect(srf, (3, 7, 18, a), (x, 78, 8, height - 154))
            pygame.draw.rect(
                srf, (4, 8, 14, min(245, a + 10)), (x, height - 118, 8, 76)
            )
        edge = pygame.Surface((36, height), pygame.SRCALPHA)
        pygame.draw.rect(edge, (96, 165, 250, 55), (0, 84, 2, height - 174))
        screen.blit(srf, (0, 0))
        screen.blit(edge, (start_x, 0))
