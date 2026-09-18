import customtkinter as ctk
import calendar
from datetime import datetime

class ModernCalendar(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        
        self.title("Seleccionar Fecha")
        self.geometry("300x320")
        self.resizable(False, False)
        
        # Opcional: Hacer la ventana "always on top" y tipo herramienta
        self.attributes("-topmost", True)
        
        # Colores consistentes con GIDEON
        self.fg_color = ("#ffffff", "#1a1a1a")
        self.btn_color = ("#e9ecef", "#2b2d31")
        self.btn_hover = ("#dee2e6", "#343a40")
        self.accent_color = "#ff7800"
        self.accent_hover = "#e66a00"
        self.text_color = ("#212529", "#ffffff")
        
        self.configure(fg_color=self.fg_color)
        
        # Fecha actual mostrada
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month
        
        # Contenedor Principal
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header (Mes/Año y controles)
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 10))
        
        self.btn_prev = ctk.CTkButton(
            self.header_frame, text="<", width=30, height=30,
            fg_color=self.btn_color, hover_color=self.btn_hover, text_color=self.text_color,
            font=ctk.CTkFont(weight="bold"), command=self.prev_month
        )
        self.btn_prev.pack(side="left")
        
        self.lbl_month_year = ctk.CTkLabel(
            self.header_frame, text="", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color=self.text_color
        )
        self.lbl_month_year.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(
            self.header_frame, text=">", width=30, height=30,
            fg_color=self.btn_color, hover_color=self.btn_hover, text_color=self.text_color,
            font=ctk.CTkFont(weight="bold"), command=self.next_month
        )
        self.btn_next.pack(side="right")
        
        # Días de la semana
        self.days_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.days_frame.pack(fill="x", pady=(0, 5))
        
        dias = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
        for i, dia in enumerate(dias):
            lbl = ctk.CTkLabel(self.days_frame, text=dia, font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888", width=35)
            lbl.grid(row=0, column=i, padx=2)
            
        # Cuadrícula de números
        self.grid_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)
        
        self.update_calendar()

    def update_calendar(self):
        # Actualizar etiqueta
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.lbl_month_year.configure(text=f"{meses[self.current_month - 1]} {self.current_year}")
        
        # Limpiar cuadrícula
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
            
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        today = datetime.now()
        
        for row, week in enumerate(cal):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                
                is_today = (day == today.day and self.current_month == today.month and self.current_year == today.year)
                
                btn = ctk.CTkButton(
                    self.grid_frame, 
                    text=str(day), 
                    width=35, height=35,
                    fg_color=self.accent_color if is_today else self.btn_color,
                    hover_color=self.accent_hover if is_today else self.btn_hover,
                    text_color="#ffffff" if is_today else self.text_color,
                    font=ctk.CTkFont(weight="bold" if is_today else "normal"),
                    command=lambda d=day: self.select_date(d)
                )
                btn.grid(row=row, column=col, padx=2, pady=2)

    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.update_calendar()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.update_calendar()
        
    def select_date(self, day):
        date_str = f"{self.current_year}-{self.current_month:02d}-{day:02d}"
        self.callback(date_str)
        self.destroy()
