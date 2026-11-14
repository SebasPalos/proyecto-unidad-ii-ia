"""Juego arcade: el jugador elige una emoción y debe convencer a la IA durante 5 segundos."""

import time

import pygame

from emotion_game import config, retro
from emotion_game.camera import Camera, frame_to_surface, to_grayscale
from emotion_game.detector import Detection, FakeDetector
from emotion_game.leaderboard import Leaderboard
from emotion_game.scoring import POSITIVE, Observation, ScoreKeeper
from emotion_game.tick_clock import TickClock

WINDOW = (1280, 720)
VIDEO = (960, 720)
PANEL_X = VIDEO[0]
PANEL_W = WINDOW[0] - VIDEO[0]

HUD_H = 70
PAD = 22

COUNTDOWN_SECONDS = 3

MENU, COUNTDOWN, PLAYING, NAME_ENTRY, RESULTS = range(5)


class EmotionGame:
    def __init__(self, detector, camera: Camera, leaderboard: Leaderboard, grayscale: bool = False):
        pygame.init()
        pygame.display.set_caption("¡Convence a la IA!")
        self.screen = pygame.display.set_mode(WINDOW)
        self.clock = pygame.time.Clock()
        self.fonts: dict[int, retro.PixelFont] = {}
        self.faces: dict[tuple, pygame.Surface] = {}
        self.crt = retro.scanlines(WINDOW, gap=3, alpha=45)
        self.stars = retro.starfield(pygame.Rect(PANEL_X + 10, 0, PANEL_W - 14, WINDOW[1]), 45, seed=7)
        self.hud_plate = pygame.Surface((VIDEO[0], HUD_H), pygame.SRCALPHA)
        self.hud_plate.fill((*retro.BG, 170))

        self.detector = detector
        self.camera = camera
        self.leaderboard = leaderboard
        self.fake_mode = isinstance(detector, FakeDetector)
        # El modelo recibe y se muestra la misma imagen, para que el jugador vea lo que ve la IA
        self.grayscale = grayscale
        self.emotions = [e for e in detector.class_names if e in config.EMOTIONS]

        self.state = MENU
        self.selected = 0
        self.keeper: ScoreKeeper | None = None
        self.tick_clock: TickClock | None = None
        self.countdown_start = 0.0
        self.player_name = ""
        self.position: int | None = None
        self.detection: Detection | None = None

    @property
    def target(self) -> str:
        return self.emotions[self.selected]

    # ------------------------------------------------------------------ ciclo

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.state == MENU:
                        running = False
                    else:
                        self._go_to_menu()
                else:
                    self._handle_event(event)

            frame = self.camera.read()
            if self.grayscale:
                frame = to_grayscale(frame)
            self.detection = self.detector.detect(frame)
            self._update()
            self._draw(frame)
            pygame.display.flip()
            self.clock.tick(60)

        self.camera.release()
        pygame.quit()

    def _handle_event(self, event) -> None:
        if self.fake_mode and event.type == pygame.KEYDOWN and self.state != NAME_ENTRY:
            self._handle_fake_keys(event.key)

        if self.state == MENU and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.emotions)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.emotions)
            elif event.key == pygame.K_g:
                # Solo en el menú: cambiar a mitad de ronda alteraría el puntaje
                self.grayscale = not self.grayscale
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = COUNTDOWN
                self.countdown_start = time.perf_counter()

        elif self.state == NAME_ENTRY:
            if event.type == pygame.TEXTINPUT:
                self.player_name = (self.player_name + event.text)[: config.NAME_MAX_LENGTH]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                elif event.key == pygame.K_RETURN and self.player_name.strip():
                    pygame.key.stop_text_input()
                    self.position = self.leaderboard.add(
                        self.target, self.player_name.strip(), self.keeper.score
                    )
                    self.state = RESULTS

        elif self.state == RESULTS and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._go_to_menu()

    def _handle_fake_keys(self, key) -> None:
        """Modo de prueba: 1-6 simulan una emoción y 0 simula que no hay rostro."""
        if key == pygame.K_0:
            self.detector.force(None)
        elif pygame.K_1 <= key <= pygame.K_9:
            index = key - pygame.K_1
            if index < len(self.emotions):
                self.detector.force(self.emotions[index])

    def _update(self) -> None:
        now = time.perf_counter()
        if self.state == COUNTDOWN and now - self.countdown_start >= COUNTDOWN_SECONDS:
            self.keeper = ScoreKeeper(self.target)
            self.tick_clock = TickClock(config.TICK_SECONDS, start=now)
            self.state = PLAYING

        elif self.state == PLAYING:
            observation = (
                Observation(self.detection.label, self.detection.conf)
                if self.detection
                else Observation(None, 0.0)
            )
            for _ in range(self.tick_clock.due(now)):
                self.keeper.tick(observation)
            if self.keeper.finished:
                self._finish_round()

    def _finish_round(self) -> None:
        self.position = None
        if self.leaderboard.qualifies(self.target, self.keeper.score):
            self.player_name = ""
            pygame.key.start_text_input()
            self.state = NAME_ENTRY
        else:
            self.state = RESULTS

    def _go_to_menu(self) -> None:
        pygame.key.stop_text_input()
        self.state = MENU


    # ------------------------------------------------------------------ dibujo

    @property
    def _now(self) -> float:
        return time.perf_counter()

    def _name(self, label: str) -> str:
        return config.EMOTIONS.get(label, label).upper()

    def _color(self, label: str):
        return retro.EMOTION_COLORS.get(label, retro.LAVENDER)

    def _hi_score(self) -> int:
        top = self.leaderboard.top(self.target)
        return top[0]["puntaje"] if top else 0

    def _draw(self, frame) -> None:
        self.screen.fill(retro.BG)
        self.screen.blit(frame_to_surface(frame, VIDEO), (0, 0))
        if not self.camera.available:
            self._text("SIN CÁMARA", 40, retro.PINK, (VIDEO[0] // 2, VIDEO[1] // 2), center=True,
                       shadow=retro.BG)
        self._draw_detection(frame.shape[1], frame.shape[0])
        self._draw_hud()
        self._draw_panel_background()

        {
            MENU: self._draw_menu,
            COUNTDOWN: self._draw_countdown,
            PLAYING: self._draw_playing,
            NAME_ENTRY: self._draw_name_entry,
            RESULTS: self._draw_results,
        }[self.state]()

        if self.fake_mode and self.state != NAME_ENTRY:
            self._text("MODO PRUEBA: 1-6 = EMOCIÓN DEL MENÚ, 0 = SIN ROSTRO", 16, retro.YELLOW,
                       (24, VIDEO[1] - 40), shadow=retro.BG)

        self._draw_bezel()
        self.screen.blit(self.crt, (0, 0))

    def _draw_hud(self) -> None:
        """Marcador superior sobre la cámara: 1UP, HI-SCORE y emoción objetivo."""
        self.screen.blit(self.hud_plate, (0, 0))
        score = self.keeper.score if self.keeper and self.state != MENU else 0
        y = 18
        self._text("1UP", 16, retro.PINK, (PAD + 8, y))
        self._text(f"{score:07d}", 16, retro.WHITE, (PAD + 8, y + 20))
        self._text("HI-SCORE", 16, retro.YELLOW, (VIDEO[0] // 2, y + 8), center=True)
        self._text(f"{self._hi_score():07d}", 16, retro.WHITE, (VIDEO[0] // 2, y + 30), center=True)
        self._text("OBJETIVO", 16, retro.CYAN, (VIDEO[0] - PAD - 8, y), right=True)
        self._text(self._name(self.target), 16, self._color(self.target),
                   (VIDEO[0] - PAD - 8, y + 20), right=True)

    def _draw_panel_background(self) -> None:
        pygame.draw.rect(self.screen, retro.BG, (PANEL_X, 0, PANEL_W, WINDOW[1]))
        for x, y, size, color in self.stars:
            # atenuadas para que no compitan con el texto del panel
            self.screen.fill(tuple(c * 2 // 5 for c in color), (x, y, size, size))

    def _draw_bezel(self) -> None:
        """Marco de máquina arcade alrededor de la cámara y del panel."""
        pygame.draw.rect(self.screen, retro.CYAN, (0, 0, VIDEO[0], VIDEO[1]), 6)
        pygame.draw.rect(self.screen, retro.PINK, (10, 10, VIDEO[0] - 20, VIDEO[1] - 20), 3)
        pygame.draw.rect(self.screen, retro.CYAN, (PANEL_X, 0, PANEL_W, WINDOW[1]), 6)

    def _draw_detection(self, frame_w: int, frame_h: int) -> None:
        if not self.detection:
            return
        sx, sy = VIDEO[0] / frame_w, VIDEO[1] / frame_h
        x1, y1, x2, y2 = self.detection.box
        rect = pygame.Rect(x1 * sx, y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy)
        is_target = self.state != MENU and self.detection.label == self.target
        color = retro.GREEN if is_target or self.state == MENU else retro.PINK

        pygame.draw.rect(self.screen, color, rect, 3)
        arm = max(16, min(rect.w, rect.h) // 5)
        for cx, cy, dx, dy in ((rect.left, rect.top, 1, 1), (rect.right, rect.top, -1, 1),
                               (rect.left, rect.bottom, 1, -1), (rect.right, rect.bottom, -1, -1)):
            for w, h in ((arm * dx, 8 * dy), (8 * dx, arm * dy)):
                corner = pygame.Rect(cx, cy, w, h)
                corner.normalize()  # normalize() corrige ancho/alto negativos en su lugar
                pygame.draw.rect(self.screen, color, corner)

        label = f"{self._name(self.detection.label)} {self.detection.conf:.0%}"
        text = self.font(20).render(label, retro.BG)
        tag = pygame.Rect(rect.left, rect.top - text.get_height() - 12, text.get_width() + 20,
                          text.get_height() + 12)
        tag.top = max(HUD_H, tag.top)
        pygame.draw.rect(self.screen, color, tag)
        self.screen.blit(text, (tag.left + 10, tag.top + 6))

    # ----- pantallas

    def _draw_title(self, y: int) -> int:
        x = PANEL_X + PAD
        self._text("¡CONVENCE", 28, retro.YELLOW, (x, y), shadow=retro.PINK)
        a_la = self.font(28).render("A LA ", retro.YELLOW)
        self._text("A LA", 28, retro.YELLOW, (x, y + 38), shadow=retro.PINK)
        self._text("IA!", 28, retro.WHITE, (x + a_la.get_width(), y + 38), shadow=retro.PINK)
        return y + 92

    def _draw_menu(self) -> None:
        x = PANEL_X + PAD
        y = self._draw_title(22)
        self._text("ELIGE TU EMOCIÓN", 16, retro.CYAN, (x, y))
        y += 30
        for i, emotion in enumerate(self.emotions):
            selected = i == self.selected
            row_y = y + i * 44
            if selected and retro.blink(self._now, 0.8):
                pygame.draw.polygon(self.screen, retro.YELLOW,
                                    [(x, row_y + 8), (x + 12, row_y + 16), (x, row_y + 24)])
            self.screen.blit(self.face(emotion, 2), (x + 20, row_y))
            color = self._color(emotion) if selected else retro.MUTED
            self._text(self._name(emotion), 24, color, (x + 62, row_y + 6))
        y += len(self.emotions) * 44 + 14

        self._text(f"TOP 5 {self._name(self.target)}", 16, retro.YELLOW, (x, y))
        self._draw_top(x, y + 28, limit=5)

        other = "COLOR" if self.grayscale else "GRISES"
        self._text(f"G: CÁMARA A {other}", 16, retro.MUTED, (x, WINDOW[1] - 104))
        self._text("FLECHAS: ELEGIR", 16, retro.MUTED, (x, WINDOW[1] - 80))
        if retro.blink(self._now, 1.0):
            self._text("ENTER: START", 24, retro.YELLOW, (x, WINDOW[1] - 50), shadow=retro.PINK)

        if retro.blink(self._now, 1.2):
            self._text("PRESIONA START", 40, retro.YELLOW, (VIDEO[0] // 2, VIDEO[1] - 100),
                       center=True, shadow=retro.PINK)

    def _draw_countdown(self) -> None:
        remaining = COUNTDOWN_SECONDS - (self._now - self.countdown_start)
        cx, cy = VIDEO[0] // 2, VIDEO[1] // 2
        self._text("¿LISTO?", 40, retro.CYAN, (cx, cy - 150), center=True, shadow=retro.BG)
        self._text(str(max(1, int(remaining) + 1)), 180, retro.YELLOW, (cx, cy + 20), center=True,
                   shadow=retro.PINK)

        x = PANEL_X + PAD
        self._text("PREPÁRATE PARA", 16, retro.CYAN, (x, 30))
        self._text(self._name(self.target), 28, self._color(self.target), (x, 56), shadow=retro.BG)
        face = self.face(self.target, 10, filled=True)
        self.screen.blit(face, (PANEL_X + (PANEL_W - face.get_width()) // 2, 120))
        for i, line in enumerate(("MANTÉN LA EMOCIÓN", "5 SEGUNDOS SEGUIDOS", "",
                                  "ENTRE MÁS TIEMPO,", "MÁS MULTIPLICADOR.")):
            self._text(line, 16, retro.WHITE, (x, 320 + i * 26))

    def _draw_playing(self) -> None:
        k = self.keeper
        x = PANEL_X + PAD
        self.screen.blit(self.face(self.target, 2), (x, 24))
        self._text(self._name(self.target), 28, self._color(self.target), (x + 44, 26), shadow=retro.BG)

        time_left = k.remaining_seconds / (config.ROUND_TICKS * config.TICK_SECONDS)
        self._text(f"TIEMPO {k.remaining_seconds:.1f}", 16, retro.CYAN, (x, 90))
        self._bar(x, 114, time_left, retro.YELLOW if time_left > 0.3 else retro.PINK)

        conf = self.detection.conf if self.detection and self.detection.label == self.target else 0.0
        self._text(f"SEGURIDAD IA {conf:.0%}", 16, retro.CYAN, (x, 156))
        self._bar(x, 180, conf, retro.GREEN)

        self._text("PUNTAJE", 16, retro.CYAN, (x, 228))
        self._text(f"{k.score:,}", 40, retro.GREEN if k.score >= 0 else retro.PINK, (x, 250),
                   shadow=retro.BG)

        if k.is_pending:
            mult_color, mult_text = retro.MUTED, f"x{k.multiplier}.."
        else:
            mult_color = retro.GREEN if k.state == POSITIVE else retro.PINK
            mult_text = f"x{k.multiplier}"
        self._text("MULTIPLICADOR", 16, retro.CYAN, (x, 330))
        self._text(mult_text, 64, mult_color, (x, 352), shadow=retro.BG)

        if k.last_delta:
            sign_color = retro.GREEN if k.last_delta > 0 else retro.PINK
            self._text(f"{k.last_delta:+,}", 28, sign_color, (x, 460))

    def _draw_name_entry(self) -> None:
        if retro.blink(self._now, 0.8):
            self._text("¡NUEVO RÉCORD!", 40, retro.YELLOW, (VIDEO[0] // 2, VIDEO[1] // 2),
                       center=True, shadow=retro.PINK)
        x = PANEL_X + PAD
        self._text("¡ENTRASTE AL TOP!", 16, retro.YELLOW, (x, 30))
        self._text(f"{self.keeper.score:,}", 40, retro.WHITE, (x, 60), shadow=retro.PINK)
        self._text("PTS", 16, retro.MUTED, (x, 112))
        self._text("ESCRIBE TU NOMBRE", 16, retro.CYAN, (x, 170))
        name = self.font(28).render(self.player_name.upper(), retro.WHITE)
        self.screen.blit(name, (x, 200))
        if retro.blink(self._now, 0.8):
            pygame.draw.rect(self.screen, retro.YELLOW,
                             (x + name.get_width() + 4, 202, 16, name.get_height() - 4))
        pygame.draw.rect(self.screen, retro.PINK, (x, 200 + name.get_height() + 6, PANEL_W - 2 * PAD, 3))
        self._text("ENTER: GUARDAR", 16, retro.MUTED, (x, 270))

    def _draw_results(self) -> None:
        k = self.keeper
        cx = VIDEO[0] // 2
        self._text("FIN DE RONDA", 40, retro.CYAN, (cx, VIDEO[1] // 2 - 60), center=True, shadow=retro.BG)
        self._text(f"{k.score:,}", 64, retro.GREEN if k.score >= 0 else retro.PINK,
                   (cx, VIDEO[1] // 2 + 20), center=True, shadow=retro.BG)

        x = PANEL_X + PAD
        self._text(self._name(self.target), 16, self._color(self.target), (x, 24))
        self._text(f"{k.score:,} PTS", 28, retro.GREEN if k.score >= 0 else retro.PINK, (x, 48),
                   shadow=retro.BG)
        held = k.target_ticks / config.ROUND_TICKS
        self._text(f"MEJOR SEGURIDAD {k.best_conf:.0%}", 16, retro.WHITE, (x, 100))
        self._text(f"CONVENCIENDO {held:.0%}", 16, retro.WHITE, (x, 124))
        if self.position:
            self._text(f"¡LUGAR #{self.position}!", 24, retro.YELLOW, (x, 158), shadow=retro.PINK)
        else:
            self._text("NO ENTRASTE AL TOP", 16, retro.MUTED, (x, 160))
        self._text(f"TOP {self._name(self.target)}", 16, retro.YELLOW, (x, 200))
        self._draw_top(x, 228, limit=config.LEADERBOARD_SIZE, highlight=self.position)
        if retro.blink(self._now, 1.0):
            self._text("ENTER: MENÚ", 24, retro.YELLOW, (x, WINDOW[1] - 50), shadow=retro.PINK)

    def _draw_top(self, x: int, y: int, limit: int, highlight: int | None = None) -> None:
        entries = self.leaderboard.top(self.target)[:limit]
        if not entries:
            self._text("AÚN NO HAY PUNTAJES", 16, retro.MUTED, (x, y))
        rank_colors = (retro.YELLOW, retro.WHITE, retro.ORANGE)
        for i, entry in enumerate(entries):
            row_y = y + i * 24
            color = rank_colors[i] if i < len(rank_colors) else retro.MUTED
            if highlight == i + 1 and retro.blink(self._now, 0.6):
                color = retro.GREEN
            score = self.font(16).render(f"{entry['puntaje']:,}", color)
            right = PANEL_X + PANEL_W - PAD
            self.screen.blit(score, (right - score.get_width(), row_y))
            # nombres largos se recortan para no chocar con el puntaje
            name = f"{i + 1:>2} {entry['nombre'].upper()}"
            while len(name) > 4 and x + self.font(16).render(name, color).get_width() > right - score.get_width() - 10:
                name = name[:-1]
            self._text(name, 16, color, (x, row_y))

    # ----- piezas

    def font(self, size: int) -> retro.PixelFont:
        if size not in self.fonts:
            self.fonts[size] = retro.PixelFont(size)
        return self.fonts[size]

    def face(self, label: str, cell: int, filled: bool = False) -> pygame.Surface:
        key = (label, cell, filled)
        if key not in self.faces:
            self.faces[key] = retro.face_surface(label, cell, filled)
        return self.faces[key]

    def _bar(self, x: int, y: int, fraction: float, color, segments: int = 16) -> None:
        """Barra segmentada en bloques, como las de vida de un arcade."""
        width, height, gap = PANEL_W - 2 * PAD, 18, 3
        block = (width - gap * (segments - 1)) / segments
        lit = retro.segments_lit(fraction, segments)
        for i in range(segments):
            bx = x + round(i * (block + gap))
            pygame.draw.rect(self.screen, color if i < lit else retro.DIM, (bx, y, round(block), height))

    def _text(self, text: str, size: int, color, pos, center=False, right=False, shadow=None) -> None:
        font = self.font(size)
        surface = font.render(text, color)
        rect = surface.get_rect()
        if center:
            rect.center = pos
        elif right:
            rect.topright = pos
        else:
            rect.topleft = pos
        if shadow is not None:
            offset = font.scale
            self.screen.blit(font.render(text, shadow), rect.move(offset, offset))
        self.screen.blit(surface, rect)
