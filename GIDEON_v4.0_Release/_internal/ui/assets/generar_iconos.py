import math
from PIL import Image, ImageDraw, ImageFont

def render_icons():
    size = 256  # Super-sampled size

    # -------------------------------------------------------------
    # 1. KPI COLA (Satélite / Antena SimpleTV)
    # -------------------------------------------------------------
    im1 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(im1)
    
    # Outer subtle circular glow/container
    d1.ellipse([20, 20, 236, 236], fill=(22, 27, 34, 180), outline=(60, 130, 246, 120), width=4)
    
    # Satellite body (tilted rect or diamond)
    # Center at (128, 128), angle 45 deg
    cx, cy = 128, 128
    
    # Solar Panels (Left and Right wings tilted)
    # Wing 1 (top-left)
    d1.polygon([(48, 64), (88, 34), (110, 64), (70, 94)], fill=(37, 99, 235, 230), outline=(96, 165, 250, 255))
    # Grid lines on wing 1
    d1.line([(68, 49), (90, 79)], fill=(147, 197, 253, 220), width=3)
    d1.line([(59, 79), (99, 49)], fill=(147, 197, 253, 220), width=3)

    # Wing 2 (bottom-right)
    d1.polygon([(146, 162), (186, 132), (208, 162), (168, 192)], fill=(37, 99, 235, 230), outline=(96, 165, 250, 255))
    # Grid lines on wing 2
    d1.line([(166, 147), (188, 177)], fill=(147, 197, 253, 220), width=3)
    d1.line([(157, 177), (197, 147)], fill=(147, 197, 253, 220), width=3)

    # Satellite center module (cylinder / cube)
    d1.rounded_rectangle([98, 98, 158, 158], radius=8, fill=(243, 244, 246, 240), outline=(255, 120, 0, 255), width=5)
    
    # Dish Antenna (bottom-left projecting wave)
    d1.arc([80, 140, 140, 200], start=110, end=250, fill=(255, 120, 0, 255), width=6)
    d1.line([(110, 150), (128, 128)], fill=(255, 120, 0, 255), width=4)
    # Signal wave
    d1.arc([55, 165, 115, 225], start=120, end=230, fill=(255, 150, 50, 200), width=4)
    d1.arc([35, 185, 95, 245], start=120, end=230, fill=(255, 180, 80, 140), width=3)

    im1 = im1.resize((128, 128), Image.Resampling.LANCZOS)
    im1.save("GIDEON_v3.3/ui/assets/kpi_cola.png")

    # -------------------------------------------------------------
    # 2. KPI EJECUCIÓN (Engranaje + Red FTTH)
    # -------------------------------------------------------------
    im2 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(im2)
    
    # Gear container
    d2.ellipse([20, 20, 236, 236], fill=(28, 25, 23, 180), outline=(245, 158, 11, 140), width=4)
    
    # Draw gear teeth
    gear_cx, gear_cy = 128, 128
    r_outer = 95
    r_inner = 75
    teeth = 8
    points = []
    for i in range(teeth * 2):
        angle = i * (math.pi / teeth)
        r = r_outer if i % 2 == 0 else r_inner
        px = gear_cx + r * math.cos(angle)
        py = gear_cy + r * math.sin(angle)
        points.append((px, py))
    d2.polygon(points, fill=(55, 65, 81, 220), outline=(251, 146, 60, 255))
    
    # Inner circle
    d2.ellipse([64, 64, 192, 192], fill=(24, 24, 27, 240), outline=(249, 115, 22, 255), width=6)
    
    # Text "FTTH" or Fiber Optic lines inside
    try:
        font = ImageFont.truetype("arialbd.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    # Draw Fiber Node symbol + FTTH text
    d2.line([(90, 105), (128, 75), (166, 105)], fill=(251, 146, 60, 255), width=5)
    d2.ellipse([84, 99, 96, 111], fill=(255, 255, 255, 255))
    d2.ellipse([122, 69, 134, 81], fill=(255, 255, 255, 255))
    d2.ellipse([160, 99, 172, 111], fill=(255, 255, 255, 255))
    
    # Text FTTH centered
    d2.text((128, 142), "FTTH", fill=(255, 180, 70, 255), font=font, anchor="mm")

    im2 = im2.resize((128, 128), Image.Resampling.LANCZOS)
    im2.save("GIDEON_v3.3/ui/assets/kpi_ejecucion.png")

    # -------------------------------------------------------------
    # 3. KPI ÉXITO (Checkmark Verde Brillante Circular)
    # -------------------------------------------------------------
    im3 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(im3)
    
    # Outer circle badge with emerald glow
    d3.ellipse([20, 20, 236, 236], fill=(16, 44, 28, 180), outline=(34, 197, 94, 140), width=4)
    d3.ellipse([36, 36, 220, 220], fill=(20, 83, 45, 220), outline=(74, 222, 128, 255), width=8)
    
    # Checkmark path
    # points: (80, 128) -> (114, 164) -> (180, 92)
    # thick polygon or connected lines
    d3.line([(76, 126), (114, 166)], fill=(255, 255, 255, 255), width=18)
    d3.line([(110, 166), (184, 90)], fill=(255, 255, 255, 255), width=18)
    # rounded ends
    d3.ellipse([67, 117, 85, 135], fill=(255, 255, 255, 255))
    d3.ellipse([175, 81, 193, 99], fill=(255, 255, 255, 255))
    d3.ellipse([105, 157, 123, 175], fill=(255, 255, 255, 255))

    im3 = im3.resize((128, 128), Image.Resampling.LANCZOS)
    im3.save("GIDEON_v3.3/ui/assets/kpi_exito.png")

    # -------------------------------------------------------------
    # 4. KPI FALLIDAS (Cable / Conector Desconectado Rojo)
    # -------------------------------------------------------------
    im4 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d4 = ImageDraw.Draw(im4)
    
    # Outer circle badge with ruby glow
    d4.ellipse([20, 20, 236, 236], fill=(45, 16, 20, 180), outline=(239, 68, 68, 140), width=4)
    
    # Two disconnected plugs:
    # Left plug (blue/grey head with orange cables)
    d4.rounded_rectangle([52, 112, 100, 144], radius=6, fill=(225, 29, 72, 240), outline=(251, 113, 133, 255), width=4)
    d4.line([(30, 128), (52, 128)], fill=(156, 163, 175, 255), width=8) # wire left
    # Pins
    d4.line([(100, 120), (116, 120)], fill=(252, 211, 77, 255), width=5)
    d4.line([(100, 136), (116, 136)], fill=(252, 211, 77, 255), width=5)
    
    # Right plug (socket/jack)
    d4.rounded_rectangle([140, 110, 188, 146], radius=6, fill=(225, 29, 72, 240), outline=(251, 113, 133, 255), width=4)
    d4.line([(188, 128), (218, 128)], fill=(156, 163, 175, 255), width=8) # wire right
    
    # Spark / Broken connection icon in middle
    # Lightning spark or 'X' in center
    d4.line([(120, 80), (136, 120)], fill=(254, 202, 202, 255), width=5)
    d4.line([(136, 120), (118, 132)], fill=(254, 202, 202, 255), width=5)
    d4.line([(118, 132), (134, 175)], fill=(254, 202, 202, 255), width=5)
    
    # Alert arcs
    d4.arc([110, 95, 146, 161], start=210, end=330, fill=(255, 100, 100, 220), width=4)

    im4 = im4.resize((128, 128), Image.Resampling.LANCZOS)
    im4.save("GIDEON_v3.3/ui/assets/kpi_fallo.png")

    print("[OK] 4 iconos KPI generados exitosamente en GIDEON_v3.3/ui/assets/")

if __name__ == "__main__":
    render_icons()
