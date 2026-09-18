def build_tab_ott(self):
    self.frame_ott_body = ctk.CTkFrame(self.tab_ott, fg_color="transparent")
    self.frame_ott_body.pack(fill="both", expand=True)

    # Panel Izquierdo: Formulario
    self.frame_ott_left = ctk.CTkScrollableFrame(self.frame_ott_body, width=370, corner_radius=12, fg_color=("#f1f3f5", "#141517"))
    self.frame_ott_left.pack(side="left", fill="both", expand=False, padx=(0, 5), pady=5)

    # --- BLOQUE: FORMULARIO OTT ---
    card_form = ctk.CTkFrame(
        self.frame_ott_left,
        corner_radius=10,
        fg_color=("#ffffff", "#1a1b1e"),
        border_width=1,
        border_color=("#ced4da", "#2c2e33")
    )
    card_form.pack(fill="x", padx=4, pady=(0, 10))

    hdr_form = ctk.CTkFrame(card_form, fg_color="transparent")
    hdr_form.pack(fill="x", padx=12, pady=(10, 8))

    ctk.CTkLabel(
        hdr_form,
        text="🎬 CONFIGURACIÓN PLAN OTT",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=("#d9480f", "#ff922b")
    ).pack(side="left")

    # Tipo de Persona
    ctk.CTkLabel(card_form, text="Tipo de Cliente:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(anchor="w", padx=12, pady=(2, 2))
    self.cmb_persona_ott = ctk.CTkSegmentedButton(
        card_form,
        values=["Persona natural", "Persona jurídica"],
        selected_color="#ff7800",
        selected_hover_color="#e66a00",
        unselected_color=("#e9ecef", "#25262b"),
        unselected_hover_color=("#dee2e6", "#343a40"),
        text_color=("#212529", "#ffffff"),
        height=30
    )
    self.cmb_persona_ott.set("Persona natural")
    self.cmb_persona_ott.pack(fill="x", padx=12, pady=(0, 8))

    # Plan OTT
    ctk.CTkLabel(card_form, text="Seleccione el Plan OTT:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(anchor="w", padx=12, pady=(2, 2))
    planes_ott_list = list(CATALOGO_OTT.keys()) if CATALOGO_OTT else ["Litesports", "Gold", "Platino", "Diamante"]
    
    self.cmb_plan_ott = ctk.CTkOptionMenu(
        card_form,
        values=planes_ott_list,
        fg_color=("#e9ecef", "#25262b"),
        button_color="#ff7800",
        button_hover_color="#e66a00",
        text_color=("#212529", "#ffffff"),
        height=30
    )
    self.cmb_plan_ott.pack(fill="x", padx=12, pady=(0, 8))

    # Fila de Cantidad
    frame_cant = ctk.CTkFrame(card_form, fg_color="transparent")
    frame_cant.pack(fill="x", padx=12, pady=(10, 10))

    ctk.CTkLabel(frame_cant, text="Cantidad de cuentas:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left")
    self.spn_cantidad_ott = ctk.CTkEntry(
        frame_cant,
        placeholder_text="1",
        width=65,
        height=28,
        fg_color=("#ffffff", "#25262b"),
        border_color=("#ced4da", "#373a40"),
        text_color=("#212529", "#f8f9fa")
    )
    self.spn_cantidad_ott.insert(0, "1")
    self.spn_cantidad_ott.pack(side="right")

    # Botones principales de adición
    ctk.CTkButton(
        card_form,
        text="➕ Agregar a la Cola OTT",
        command=self.agregar_lote_ott,
        fg_color="#ff7800",
        hover_color="#e66a00",
        text_color="#ffffff",
        font=ctk.CTkFont(size=13, weight="bold"),
        height=34
    ).pack(fill="x", padx=12, pady=(0, 12))

    # --- PANEL DERECHO: COLA OTT ---
    self.frame_ott_right = ctk.CTkFrame(self.frame_ott_body, corner_radius=12, fg_color="transparent")
    self.frame_ott_right.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=5)

    card_cola = ctk.CTkFrame(
        self.frame_ott_right,
        corner_radius=10,
        fg_color=("#ffffff", "#1a1b1e"),
        border_width=1,
        border_color=("#ced4da", "#2c2e33")
    )
    card_cola.pack(fill="both", expand=True, padx=0, pady=0)
    
    ctk.CTkLabel(
        card_cola, 
        text="Cola de Ejecución y Consola compartida con el Centro de Control.", 
        font=ctk.CTkFont(size=14, slant="italic"),
        text_color=("#868e96", "#adb5bd")
    ).pack(expand=True)
