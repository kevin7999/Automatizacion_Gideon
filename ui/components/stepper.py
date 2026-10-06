import customtkinter as ctk
from ui.theme import *

class StepperItem(ctk.CTkFrame):
    def __init__(self, master, step_num: int, label: str, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.step_num = step_num
        self.label = label
        
        # Circle indicator
        self.circle = ctk.CTkFrame(
            self, 
            width=24, 
            height=24, 
            corner_radius=12,
            fg_color=BG_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE
        )
        self.circle.pack(side="left", padx=(0, 8))
        self.circle.pack_propagate(False)
        
        self.lbl_num = ctk.CTkLabel(
            self.circle, 
            text=str(self.step_num), 
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_SECONDARY
        )
        self.lbl_num.place(relx=0.5, rely=0.5, anchor="center")
        
        # Label text
        self.lbl_text = ctk.CTkLabel(
            self,
            text=self.label,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        self.lbl_text.pack(side="left")

    def set_state(self, state: str):
        """states: 'pending', 'active', 'success', 'error'"""
        if state == "pending":
            self.circle.configure(fg_color=BG_INPUT, border_color=BORDER_SUBTLE)
            self.lbl_num.configure(text=str(self.step_num), text_color=TEXT_SECONDARY)
            self.lbl_text.configure(text_color=TEXT_SECONDARY, font=FONT_BODY)
        elif state == "active":
            self.circle.configure(fg_color=BG_CARD, border_color=PRIMARY_ORANGE)
            self.lbl_num.configure(text=str(self.step_num), text_color=PRIMARY_ORANGE)
            self.lbl_text.configure(text_color=PRIMARY_ORANGE, font=FONT_BODY_BOLD)
        elif state == "success":
            self.circle.configure(fg_color=STATUS_SUCCESS, border_color=STATUS_SUCCESS)
            self.lbl_num.configure(text="✓", text_color=BG_APP)
            self.lbl_text.configure(text_color=TEXT_PRIMARY, font=FONT_BODY)
        elif state == "error":
            self.circle.configure(fg_color=STATUS_ERROR, border_color=STATUS_ERROR)
            self.lbl_num.configure(text="!", text_color=BG_APP)
            self.lbl_text.configure(text_color=STATUS_ERROR, font=FONT_BODY)


class Stepper(ctk.CTkFrame):
    """
    Pipeline visual de progreso.
    Uso: stepper = Stepper(parent, steps=["Login", "Datos", "OTP"])
    stepper.set_step(2, "active")
    """
    def __init__(self, master, steps: list, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.items = []
        self.steps_config = steps
        
        for i, text in enumerate(steps, start=1):
            item = StepperItem(self, step_num=i, label=text)
            item.pack(side="left", padx=(0, 20))
            self.items.append(item)
            
            # Draw line between items if not the last one
            if i < len(steps):
                line = ctk.CTkFrame(self, width=30, height=2, fg_color=BORDER_SUBTLE)
                line.pack(side="left", padx=(0, 20))
                
    def reset(self):
        for item in self.items:
            item.set_state("pending")

    def set_step(self, step_index: int, state: str):
        """step_index es 0-based. Ej: 0 es Login"""
        if 0 <= step_index < len(self.items):
            self.items[step_index].set_state(state)
