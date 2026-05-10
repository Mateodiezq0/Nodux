# Nodux

**Nodux** es una herramienta de análisis de estructuras en 3D.
Está pensada para ingenieros, estudiantes y cualquier persona que necesite
calcular cómo se comporta una estructura (como un pórtico o una viga) cuando
se le aplican cargas o fuerzas.

<img width="1918" height="1138" alt="image" src="https://github.com/user-attachments/assets/bfc7931f-c1de-42f4-a7f8-eebf7f9c45ec" />


---

## ¿Qué hace Nodux?

Cuando construís un edificio, un puente o cualquier estructura, necesitás saber
si va a aguantar el peso y las fuerzas que va a recibir. Nodux te permite:

- **Definir tu estructura** describiendo sus nodos (puntos de unión), barras
  (elementos que los conectan), materiales y cargas en un archivo de texto
  simple (formato JSON o YAML).
- **Calcular automáticamente** cuánto se deforma cada parte y qué fuerzas
  internas aparecen en cada barra.
- **Ver los resultados en 3D** con gráficos interactivos: podés rotar la
  estructura, ver la deformada y los diagramas de esfuerzos.
- **Exportar los resultados** a Excel, PDF o CSV para usarlos en informes o
  seguir trabajando con ellos.

---

## ¿Para quién es?

- Estudiantes de ingeniería civil o arquitectura que quieran verificar
  ejercicios de estructuras.
- Profesionales que necesiten una herramienta liviana para análisis rápidos.
- Cualquier persona curiosa que quiera entender cómo se calculan estructuras.

---

## ¿Cómo funciona por dentro?

No hace falta entender el código para usar Nodux, pero si te interesa saber
cómo está organizado, el proyecto tiene cuatro partes principales:

```
Nodux/
│
├── core/   → El "cerebro" matemático.
│            Aquí viven los cálculos: nodos, barras, cargas y la
│            resolución del sistema de ecuaciones.
│
├── cli/    → La "puerta de entrada".
│            Lee los archivos de modelo (JSON/YAML), coordina el
│            análisis y muestra la interfaz gráfica de escritorio.
│            También genera los reportes en Excel, PDF y CSV.
│
├── plot/   → Los gráficos.
│            Genera las visualizaciones 2D (matplotlib) y las vistas
│            3D interactivas (PyVista).
│
└── docs/   → La documentación.
             Guías de uso, descripción de la arquitectura y formato
             de los archivos de modelo.
```

### El flujo de trabajo, paso a paso

```
Tu archivo JSON/YAML
        ↓
Nodux lo lee y construye el modelo
        ↓
Calcula desplazamientos y esfuerzos
        ↓
Muestra los resultados en pantalla (3D)
        ↓
Exporta a Excel / PDF / CSV
```

---

## ¿Qué necesito para usarlo?

Solo necesitás tener **Python** instalado en tu computadora. El resto de las
dependencias se instalan con un solo comando.

### Instalación

```bash
# 1. Crear un entorno virtual (recomendado)
python -m venv .venv

# 2. Activarlo
# En Windows:
.\.venv\Scripts\Activate.ps1
# En Mac/Linux:
source .venv/bin/activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

### Abrir la interfaz gráfica

```bash
python -m cli gui
```

### Probar con un ejemplo incluido

```bash
python -m cli gui --ejemplo
```

Este comando carga una estructura de ejemplo para que puedas ver Nodux en
acción sin necesidad de crear ningún archivo.

### Analizar tu propio modelo

```bash
python -m cli run ruta/a/tu/modelo.json
```

> **Importante:** siempre ejecutá los comandos desde la carpeta raíz del
> proyecto (donde está el archivo `README.md`).

---

## Formato del modelo

Los modelos se describen en archivos JSON o YAML. En la carpeta
`cli/examples/` encontrás un ejemplo completo (`supertesteo_like.json`) que
podés usar como punto de partida.

Un modelo define:

- **Nodos:** los puntos de la estructura (con sus coordenadas x, y, z).
- **Barras:** las conexiones entre nodos (con su material y sección).
- **Cargas:** fuerzas puntuales, distribuidas o en los nodos.
- **Apoyos:** qué nodos están fijos y en qué direcciones.

---

## Limitaciones actuales

Nodux está enfocado en estructuras reticuladas 3D lineales (pórticos y vigas
espaciales). No es un software de diseño normativo completo ni un procesador
CAD genérico: su objetivo es ir del modelo al cálculo y a la visualización de
forma directa y eficiente.

---

## Más información

La carpeta `docs/` contiene guías más detalladas sobre cada parte del sistema,
incluyendo el formato completo del modelo y cómo funciona la interfaz gráfica.
