import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# Configuración de las 4 vigas (Cuadrado de 10x10)
beams = [
    {'origin': [0, 0, 0], 'L': 10, 'dir': 'x'},
    {'origin': [0, 10, 0], 'L': 10, 'dir': 'x'},
    {'origin': [0, 0, 0], 'L': 10, 'dir': 'y'},
    {'origin': [10, 0, 0], 'L': 10, 'dir': 'y'}
]

fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
plt.subplots_adjust(bottom=0.2)

# Almacenes para objetos gráficos que se deben actualizar
moment_patches = []
beam_lines = []

def update_plot(scale):
    global moment_patches, beam_lines
    
    # Limpiar dibujos anteriores
    for p in moment_patches: p.remove()
    for line in beam_lines: line.pop(0).remove()
    moment_patches.clear()
    beam_lines.clear()

    for b in beams:
        s = np.linspace(0, b['L'], 50)
        
        # 1. Ecuación de Momento (Parábola)
        m_vals = 0.5 * 5 * s * (b['L'] - s) * scale
        
        # 2. Ecuación de Deformación (Elástica simplificada)
        # y = (w*x / 24*E*I) * (L^3 - 2*L*x^2 + x^3)
        deflec = - (0.02 * s * (b['L']**3 - 2*b['L']*s**2 + s**3)) * scale

        # Determinar coordenadas según dirección
        if b['dir'] == 'x':
            X, Y = b['origin'][0] + s, np.full_like(s, b['origin'][1])
        else:
            X, Y = np.full_like(s, b['origin'][0]), b['origin'][1] + s

        # 3. Dibujar la viga deformada
        line = ax.plot(X, Y, deflec, color='black', lw=3, linestyle='--')
        beam_lines.append(line)

        # 4. Dibujar el diagrama de momentos sobre la viga deformada
        Z_top = deflec + m_vals
        verts = [(X[i], Y[i], deflec[i]) for i in range(len(s))] + \
                [(X[i], Y[i], Z_top[i]) for i in range(len(s)-1, -1, -1)]
        
        poly = Poly3DCollection([verts], facecolors='cyan', alpha=0.5, edgecolors='blue', lw=0.5)
        ax.add_collection3d(poly)
        moment_patches.append(poly)

    ax.set_zlim(-20, 50) # Ajuste de límites para ver ambos efectos
    fig.canvas.draw_idle()

# Configuración Slider
ax_slider = plt.axes([0.25, 0.05, 0.5, 0.03])
slider = Slider(ax_slider, 'Factor de Carga', 0.1, 10.0, valinit=1.0)
slider.on_changed(update_plot)

# Configuración estética
ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_zlabel('Esfuerzo / Deflexión')
ax.set_title('Estructura 3D: Momentos (Cian) y Deformada (Punteada)')
ax.view_init(elev=25, azim=-35)

update_plot(1.0)
plt.show()