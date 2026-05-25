"""
LED Light Ring Simulator for WinVE.
Provides standard smart-speaker visual light response states (listening, thinking, speaking, idle, warning)
using Flet canvas shapes and animations for HUDs or hardware-in-the-loop emulation.
"""
import flet as ft
import math
import time
import threading

class LedRingSimulator(ft.UserControl):
    """Simulates a circular LED array displaying smart assistant animation states."""
    
    def __init__(self, led_count=12, radius=80, led_radius=10):
        super().__init__()
        self.led_count = led_count
        self.radius = radius
        self.led_radius = led_radius
        self.state = "IDLE" # IDLE, LISTENING, THINKING, SPEAKING, ERROR
        self.colors = [ft.colors.GREY_900] * led_count
        self.running = False
        self.canvas = None
        self.angle_offset = 0
        self.pulse_val = 0
        
    def build(self):
        # We use a basic Canvas to draw the circular ring of LEDs
        self.canvas = ft.Canvas(
            width=2 * (self.radius + self.led_radius) + 20,
            height=2 * (self.radius + self.led_radius) + 20,
        )
        self._update_leds()
        return self.canvas

    def did_mount(self):
        self.running = True
        self.anim_thread = threading.Thread(target=self._animate_loop, daemon=True)
        self.anim_thread.start()

    def will_unmount(self):
        self.running = False

    def set_state(self, new_state):
        """Sets the animation state (IDLE, LISTENING, THINKING, SPEAKING, ERROR)."""
        self.state = new_state.upper()
        print(f"🌈 LED State changed to: {self.state}")

    def _animate_loop(self):
        frame = 0
        while self.running:
            frame += 1
            self.angle_offset = (frame * 0.15) % (2 * math.pi)
            self.pulse_val = 0.5 + 0.5 * math.sin(frame * 0.2)
            
            self._update_colors()
            self._update_leds()
            
            try:
                self.canvas.update()
            except Exception:
                pass
            time.sleep(0.04) # ~25 FPS

    def _update_colors(self):
        """Configures LED color intensities depending on state."""
        if self.state == "IDLE":
            # Very slow, low-intensity pulse of amber or dim white
            for i in range(self.led_count):
                intensity = int(20 + 30 * self.pulse_val)
                self.colors[i] = f"#05{intensity:02x}{intensity:02x}" # Dim cyan-blue
                
        elif self.state == "LISTENING":
            # Solid bright blue, with one pulsing cyan light pointing to "direction" (simulated)
            for i in range(self.led_count):
                self.colors[i] = ft.colors.BLUE_A400
            # Pulse the top light
            pulse_int = int(150 + 105 * self.pulse_val)
            self.colors[0] = f"#00{pulse_int:02x}ff"
            
        elif self.state == "THINKING":
            # Spinning blue/cyan lights (chasing pattern)
            for i in range(self.led_count):
                angle = (i / self.led_count) * 2 * math.pi
                diff = (angle - self.angle_offset) % (2 * math.pi)
                intensity = int(255 * (1 - (diff / (2 * math.pi))))
                self.colors[i] = f"#00{intensity:02x}ff"
                
        elif self.state == "SPEAKING":
            # Bright blue breathing/pulsing amplitude animation
            for i in range(self.led_count):
                intensity = int(100 + 155 * self.pulse_val)
                self.colors[i] = f"#00{intensity:02x}{intensity:02x}"
                
        elif self.state == "ERROR":
            # Rapid flashing red
            flash = (int(time.time() * 8) % 2) == 0
            for i in range(self.led_count):
                self.colors[i] = ft.colors.RED_600 if flash else ft.colors.RED_900

    def _update_leds(self):
        """Redraws the individual circles representing LEDs on the Canvas."""
        if not self.canvas:
            return
            
        self.canvas.shapes.clear()
        
        center_x = self.radius + self.led_radius + 10
        center_y = self.radius + self.led_radius + 10
        
        for i in range(self.led_count):
            angle = (i / self.led_count) * 2 * math.pi
            x = center_x + self.radius * math.cos(angle)
            y = center_y + self.radius * math.sin(angle)
            
            # Add LED circle
            self.canvas.shapes.append(
                ft.cv.Circle(
                    x=x,
                    y=y,
                    radius=self.led_radius,
                    paint=ft.Paint(
                        color=self.colors[i],
                        style=ft.PaintingStyle.FILL
                    )
                )
            )

def main(page: ft.Page):
    page.title = "WinVE LED Animation Simulator"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 500
    
    sim = LedRingSimulator(led_count=16, radius=100, led_radius=12)
    
    def set_idle(e): sim.set_state("IDLE")
    def set_listen(e): sim.set_state("LISTENING")
    def set_think(e): sim.set_state("THINKING")
    def set_speak(e): sim.set_state("SPEAKING")
    def set_error(e): sim.set_state("ERROR")
    
    page.add(
        ft.Column([
            ft.Container(
                content=sim,
                alignment=ft.alignment.center,
                padding=20
            ),
            ft.Row([
                ft.ElevatedButton("Idle", on_click=set_idle),
                ft.ElevatedButton("Listen", on_click=set_listen),
                ft.ElevatedButton("Think", on_click=set_think),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                ft.ElevatedButton("Speak", on_click=set_speak),
                ft.ElevatedButton("Error", on_click=set_error),
            ], alignment=ft.MainAxisAlignment.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

if __name__ == "__main__":
    ft.app(target=main)
