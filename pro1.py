import pandas as pd
import tkinter as tk
from tkinter import ttk
import threading
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


RUTA_ARCHIVO = "./PROYECTO EXAMEN UNI 2/ventas wal.csv"
LIMITE_PRODUCTOS = 50
LIMITE_RESULTADOS = 200

plt.style.use("dark_background")


def cargar_datos():
    df = pd.read_csv(RUTA_ARCHIVO, sep=";")
    df = df.dropna(subset=["Item_Identifier", "Outlet_Identifier"])
    df["Item_Fat_Content"] = df["Item_Fat_Content"].replace({
        "LF": "Low Fat",
        "low fat": "Low Fat",
        "reg": "Regular"
    })
    df["Item_Identifier"] = df["Item_Identifier"].astype(str)
    df["Outlet_Identifier"] = df["Outlet_Identifier"].astype(str)
    return df


datos = cargar_datos()

top50 = datos["Item_Identifier"].value_counts().head(LIMITE_PRODUCTOS).index.tolist()
tipos_disponibles = sorted(datos["Item_Type"].dropna().unique().tolist())

cache_tipo  = {}
cache_nombre = {}
for codigo in top50:
    fila = datos[datos["Item_Identifier"] == codigo]
    tipo = str(fila.iloc[0]["Item_Type"]) if len(fila) > 0 else ""
    cache_tipo[codigo]   = tipo
    cache_nombre[codigo] = f"{codigo} ({tipo})" if tipo else codigo


def nombre_producto(codigo):
    return cache_nombre.get(codigo, codigo)

def tipo_producto(codigo):
    return cache_tipo.get(codigo, "")

def filtro_tipo_activo(a, b):
    seleccion = combo_tipo.get()
    if seleccion == "Todos":
        return True
    return seleccion in (tipo_producto(a), tipo_producto(b))

def mostrar_estado(texto, color="gray"):
    ventana.after(0, lambda: label_estado.config(text=texto, fg=color))

def limpiar_tabla():
    ventana.after(0, lambda: [tabla.delete(i) for i in tabla.get_children()])

def mostrar_resultados(lista):
    lista_ordenada = sorted(lista, key=lambda x: x[2], reverse=True)[:LIMITE_RESULTADOS]
    for fila in lista_ordenada:
        ventana.after(0, lambda f=fila: tabla.insert("", tk.END, values=f))


def algoritmo_apriori(soporte_min):
    mostrar_estado("Calculando Apriori...", "blue")
    limpiar_tabla()

    df = datos[datos["Item_Identifier"].isin(top50)]
    transacciones = df.groupby("Outlet_Identifier")["Item_Identifier"].apply(list).to_dict()
    total = len(transacciones)
    minimo = total * soporte_min

    try:
        frec_min = int(entrada_frec_min.get()) if entrada_frec_min.get().strip() else 0
        frec_max = int(entrada_frec_max.get()) if entrada_frec_max.get().strip() else 99999
    except ValueError:
        mostrar_estado("Error: los valores de frecuencia deben ser numeros enteros", "red")
        return

    conteo = {}
    for productos in transacciones.values():
        productos = sorted(set(productos))
        for i in range(len(productos)):
            for j in range(i + 1, len(productos)):
                par = (productos[i], productos[j])
                conteo[par] = conteo.get(par, 0) + 1

    resultados = []
    for (a, b), veces in conteo.items():
        if veces >= minimo and frec_min <= veces <= frec_max and filtro_tipo_activo(a, b):
            porcentaje = f"{round((veces / total) * 100, 2)}%"
            resultados.append((nombre_producto(a), nombre_producto(b), veces, porcentaje))

    mostrar_resultados(resultados)
    mostrar_estado(f"Apriori listo — {len(resultados)} pares encontrados", "green")


def algoritmo_vertical(soporte_min):
    mostrar_estado("Calculando Vertical...", "blue")
    limpiar_tabla()

    df = datos[datos["Item_Identifier"].isin(top50)]
    tidlists = df.groupby("Item_Identifier")["Outlet_Identifier"].apply(set).to_dict()
    total = len(df["Outlet_Identifier"].unique())
    minimo = total * soporte_min

    try:
        frec_min = int(entrada_frec_min.get()) if entrada_frec_min.get().strip() else 0
        frec_max = int(entrada_frec_max.get()) if entrada_frec_max.get().strip() else 99999
    except ValueError:
        mostrar_estado("Error: los valores de frecuencia deben ser numeros enteros", "red")
        return

    items = list(tidlists.keys())
    resultados = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            comunes = len(tidlists[a] & tidlists[b])
            if comunes >= minimo and frec_min <= comunes <= frec_max and filtro_tipo_activo(a, b):
                porcentaje = f"{round((comunes / total) * 100, 2)}%"
                resultados.append((nombre_producto(a), nombre_producto(b), comunes, porcentaje))

    mostrar_resultados(resultados)
    mostrar_estado(f"Vertical listo — {len(resultados)} pares encontrados", "green")


def algoritmo_lift(soporte_min):
    mostrar_estado("Calculando Lift...", "blue")
    limpiar_tabla()

    df = datos[datos["Item_Identifier"].isin(top50)]
    transacciones = df.groupby("Outlet_Identifier")["Item_Identifier"].apply(list).to_dict()
    total = len(transacciones)

    frecuencia = {}
    for productos in transacciones.values():
        for item in productos:
            frecuencia[item] = frecuencia.get(item, 0) + 1

    conteo = {}
    for productos in transacciones.values():
        productos = sorted(set(productos))
        for i in range(len(productos)):
            for j in range(i + 1, len(productos)):
                par = (productos[i], productos[j])
                conteo[par] = conteo.get(par, 0) + 1

    operador = combo_lift_op.get()
    valor    = float(entrada_lift_val.get())

    def cumple_lift(lift):
        ops = {">": lift > valor, "<": lift < valor, ">=": lift >= valor, "<=": lift <= valor, "=": lift == valor}
        return ops.get(operador, False)

    def etiqueta_lift(lift):
        if lift > 1:   return "Correlacion positiva"
        if lift < 1:   return "Correlacion negativa"
        return "Independencia"

    resultados = []
    for (a, b), veces in conteo.items():
        sop_ab = veces / total
        sop_a  = frecuencia[a] / total
        sop_b  = frecuencia[b] / total
        lift   = round(sop_ab / (sop_a * sop_b), 2)

        if cumple_lift(lift) and filtro_tipo_activo(a, b):
            resultados.append((nombre_producto(a), nombre_producto(b), lift, etiqueta_lift(lift)))

    mostrar_resultados(resultados)
    mostrar_estado(f"Lift listo — {len(resultados)} pares encontrados", "green")


def info_dataset():
    limpiar_tabla()
    info = [
        ("Filas totales",       len(datos),                                  "", ""),
        ("Columnas totales",    len(datos.columns),                          "", ""),
        ("Tiendas unicas",      len(datos["Outlet_Identifier"].unique()),     "", ""),
        ("Productos unicos",    len(datos["Item_Identifier"].unique()),       "", ""),
        ("--- COLUMNAS ---",    "", "", ""),
    ]
    for col in datos.columns:
        info.append((col, "", "", ""))
    for fila in info:
        ventana.after(0, lambda f=fila: tabla.insert("", tk.END, values=f))
    mostrar_estado("Info del dataset cargada", "green")


def ejecutar(metodo):
    try:
        soporte = float(entrada_soporte.get())
    except ValueError:
        mostrar_estado("Error: el soporte debe ser un numero (ej: 0.4)", "red")
        return

    mapa = {
        "APRIORI":  lambda: algoritmo_apriori(soporte),
        "VERTICAL": lambda: algoritmo_vertical(soporte),
        "LIFT":     lambda: algoritmo_lift(soporte),
        "INFO":     lambda: info_dataset(),
    }
    threading.Thread(target=mapa[metodo]).start()


def abrir_graficas():

    df = datos[datos["Item_Identifier"].isin(top50)]
    transacciones = df.groupby("Outlet_Identifier")["Item_Identifier"].apply(list).to_dict()
    total = len(transacciones)

    ventas_por_producto = (
        df.groupby("Item_Identifier")["Item_Outlet_Sales"]
        .sum().sort_values(ascending=False).head(10)
    )
    ventas_por_producto.index = [cache_nombre.get(c, c) for c in ventas_por_producto.index]

    ventas_por_tipo = (
        df.groupby("Item_Type")["Item_Outlet_Sales"]
        .sum().sort_values(ascending=False)
    )

    conteo_pares = {}
    frecuencia = {}
    for productos in transacciones.values():
        productos_unicos = sorted(set(productos))
        for item in productos_unicos:
            frecuencia[item] = frecuencia.get(item, 0) + 1
        for i in range(len(productos_unicos)):
            for j in range(i + 1, len(productos_unicos)):
                par = (productos_unicos[i], productos_unicos[j])
                conteo_pares[par] = conteo_pares.get(par, 0) + 1

    pares_top = sorted(conteo_pares, key=conteo_pares.get, reverse=True)[:10]
    nombres_pares = [f"{cache_nombre.get(p[0],p[0])}\n& {cache_nombre.get(p[1],p[1])}" for p in pares_top]
    valores_pares = [conteo_pares[p] for p in pares_top]

    positivos = negativos = independientes = 0
    for (a, b), veces in conteo_pares.items():
        sop_ab = veces / total
        sop_a  = frecuencia[a] / total
        sop_b  = frecuencia[b] / total
        lift = sop_ab / (sop_a * sop_b)
        if   lift > 1: positivos     += 1
        elif lift < 1: negativos     += 1
        else:          independientes += 1

    grasa = datos["Item_Fat_Content"].value_counts()

    ventas_por_outlet = (
        df.groupby("Outlet_Identifier")["Item_Outlet_Sales"]
        .sum().sort_values(ascending=False)
    )

    COLOR_FONDO    = "#0d1117"
    COLOR_PANEL    = "#161b22"
    COLOR_TEXTO    = "#e6edf3"
    PALETA_BARRAS  = ["#58a6ff","#3fb950","#d29922","#f78166","#79c0ff",
                      "#56d364","#e3b341","#ff7b72","#a5d6ff","#7ee787"]
    PALETA_PIE     = ["#58a6ff","#3fb950","#d29922","#f78166","#a5d6ff"]

    def crear_tab(notebook, titulo):
        frame = tk.Frame(notebook, bg=COLOR_FONDO)
        notebook.add(frame, text=titulo)
        return frame

    def nueva_figura(alto=6, ancho=11):
        fig, ax = plt.subplots(figsize=(ancho, alto))
        fig.patch.set_facecolor(COLOR_FONDO)
        return fig, ax

    def estilizar_eje(ax, titulo, xlabel="", ylabel=""):
        ax.set_facecolor(COLOR_PANEL)
        ax.set_title(titulo, color=COLOR_TEXTO, fontsize=13, pad=12)
        ax.set_xlabel(xlabel, color=COLOR_TEXTO)
        ax.set_ylabel(ylabel, color=COLOR_TEXTO)
        ax.tick_params(colors=COLOR_TEXTO)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")
        ax.grid(axis="y", color="#30363d", linewidth=0.5)

    def incrustar_figura(fig, frame):
        plt.tight_layout(pad=2.5)
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    ven = tk.Toplevel(ventana)
    ven.title("Dashboard Analitico — Walmart")
    ven.geometry("1150x720")
    ven.configure(bg=COLOR_FONDO)

    notebook = ttk.Notebook(ven)
    notebook.pack(fill="both", expand=True)

    tab1 = crear_tab(notebook, "Top Productos")
    fig1, ax = nueva_figura()
    barras = ax.bar(ventas_por_producto.index, ventas_por_producto.values,
                    color=PALETA_BARRAS, edgecolor=COLOR_FONDO, linewidth=0.8)
    for barra in barras:
        alto = barra.get_height()
        ax.text(barra.get_x() + barra.get_width() / 2, alto * 1.01,
                f"{alto:,.0f}", ha="center", va="bottom", color=COLOR_TEXTO, fontsize=8)
    estilizar_eje(ax, "Top 10 Productos por Ventas Totales", ylabel="Ventas ($)")
    ax.tick_params(axis="x", rotation=40)
    incrustar_figura(fig1, tab1)

    tab2 = crear_tab(notebook, "Conjuntos Frecuentes")
    fig2, ax2 = nueva_figura()
    barras2 = ax2.barh(nombres_pares[::-1], valores_pares[::-1],
                       color=PALETA_BARRAS, edgecolor=COLOR_FONDO)
    for barra in barras2:
        ancho = barra.get_width()
        ax2.text(ancho + 0.3, barra.get_y() + barra.get_height() / 2,
                 str(int(ancho)), va="center", color=COLOR_TEXTO, fontsize=9)
    estilizar_eje(ax2, "Top 10 Pares de Productos Mas Frecuentes", xlabel="Apariciones")
    ax2.grid(axis="x", color="#30363d", linewidth=0.5)
    ax2.grid(axis="y", visible=False)
    incrustar_figura(fig2, tab2)

    tab3 = crear_tab(notebook, "Correlaciones Lift")
    fig3, ax3 = nueva_figura(alto=6, ancho=10)
    etiquetas_lift = ["Positiva\n(lift > 1)", "Independencia\n(lift = 1)", "Negativa\n(lift < 1)"]
    colores_lift   = ["#3fb950", "#d29922", "#f78166"]
    valores_lift   = [positivos, independientes, negativos]
    wedges, texts, autotexts = ax3.pie(
        valores_lift, labels=etiquetas_lift, autopct="%1.1f%%",
        colors=colores_lift, startangle=90, shadow=False,
        textprops={"color": COLOR_TEXTO, "fontsize": 11},
        wedgeprops={"linewidth": 2, "edgecolor": COLOR_FONDO}
    )
    for at in autotexts:
        at.set_fontsize(10)
    ax3.set_title("Distribucion de Tipos de Correlacion (Lift)", color=COLOR_TEXTO, fontsize=13)
    incrustar_figura(fig3, tab3)

    tab4 = crear_tab(notebook, "Contenido de Grasa")
    fig4, ax4 = nueva_figura(alto=6, ancho=10)
    wedges4, texts4, autotexts4 = ax4.pie(
        grasa.values, labels=grasa.index, autopct="%1.1f%%",
        colors=PALETA_PIE, startangle=90, shadow=False,
        textprops={"color": COLOR_TEXTO, "fontsize": 12},
        wedgeprops={"linewidth": 2, "edgecolor": COLOR_FONDO}
    )
    ax4.set_title("Distribucion de Contenido de Grasa en Productos", color=COLOR_TEXTO, fontsize=13)
    incrustar_figura(fig4, tab4)

    tab5 = crear_tab(notebook, "Ventas por Tienda")
    fig5, ax5 = nueva_figura()
    barras5 = ax5.bar(ventas_por_outlet.index, ventas_por_outlet.values,
                      color=PALETA_BARRAS, edgecolor=COLOR_FONDO)
    for barra in barras5:
        alto = barra.get_height()
        ax5.text(barra.get_x() + barra.get_width() / 2, alto * 1.01,
                 f"{alto:,.0f}", ha="center", va="bottom", color=COLOR_TEXTO, fontsize=8)
    estilizar_eje(ax5, "Ventas Totales por Tienda (Outlet)", ylabel="Ventas ($)")
    ax5.tick_params(axis="x", rotation=30)
    incrustar_figura(fig5, tab5)

    tab6 = crear_tab(notebook, "Ventas por Categoria")
    fig6, ax6 = nueva_figura(alto=6, ancho=12)
    barras6 = ax6.barh(ventas_por_tipo.index[::-1], ventas_por_tipo.values[::-1],
                       color=PALETA_BARRAS, edgecolor=COLOR_FONDO)
    for barra in barras6:
        ancho = barra.get_width()
        ax6.text(ancho + 100, barra.get_y() + barra.get_height() / 2,
                 f"{ancho:,.0f}", va="center", color=COLOR_TEXTO, fontsize=8)
    estilizar_eje(ax6, "Ventas Totales por Categoria de Producto", xlabel="Ventas ($)")
    ax6.grid(axis="x", color="#30363d", linewidth=0.5)
    ax6.grid(axis="y", visible=False)
    incrustar_figura(fig6, tab6)


ventana = tk.Tk()
ventana.title("Mineria de Datos — Walmart")
ventana.geometry("1050x700")
ventana.configure(bg="#f5f5f5")

frame_controles = tk.Frame(ventana, bg="#f5f5f5", pady=8)
frame_controles.pack(fill=tk.X, padx=15)

tk.Label(frame_controles, text="Soporte minimo (0.0 a 1.0):", bg="#f5f5f5").grid(row=0, column=0, padx=5, sticky="w")
entrada_soporte = tk.Entry(frame_controles, width=8)
entrada_soporte.insert(0, "0.40")
entrada_soporte.grid(row=0, column=1, padx=5)

tk.Label(frame_controles, text="Filtrar por tipo de producto:", bg="#f5f5f5").grid(row=0, column=2, padx=(20, 5), sticky="w")
combo_tipo = ttk.Combobox(frame_controles, values=["Todos"] + tipos_disponibles, width=28, state="readonly")
combo_tipo.current(0)
combo_tipo.grid(row=0, column=3, padx=5)

frame_lift = tk.Frame(ventana, bg="#f5f5f5", pady=4)
frame_lift.pack(fill=tk.X, padx=15)

tk.Label(frame_lift, text="Filtro Frecuencia (Apriori/Vertical) — entre:", bg="#f5f5f5").pack(side=tk.LEFT, padx=5)
entrada_frec_min = tk.Entry(frame_lift, width=6)
entrada_frec_min.insert(0, "")
entrada_frec_min.pack(side=tk.LEFT, padx=3)
tk.Label(frame_lift, text="y", bg="#f5f5f5").pack(side=tk.LEFT)
entrada_frec_max = tk.Entry(frame_lift, width=6)
entrada_frec_max.insert(0, "")
entrada_frec_max.pack(side=tk.LEFT, padx=3)
tk.Label(frame_lift, text="apariciones  (dejar vacio = sin limite)", fg="gray", bg="#f5f5f5").pack(side=tk.LEFT, padx=5)

frame_lift2 = tk.Frame(ventana, bg="#f5f5f5", pady=4)
frame_lift2.pack(fill=tk.X, padx=15)

tk.Label(frame_lift2, text="Filtro para Lift — mostrar pares con lift:", bg="#f5f5f5").pack(side=tk.LEFT, padx=5)
combo_lift_op = ttk.Combobox(frame_lift2, values=[">", "<", ">=", "<=", "="], width=5, state="readonly")
combo_lift_op.current(2)
combo_lift_op.pack(side=tk.LEFT, padx=3)
entrada_lift_val = tk.Entry(frame_lift2, width=8)
entrada_lift_val.insert(0, "1.0")
entrada_lift_val.pack(side=tk.LEFT, padx=3)
tk.Label(frame_lift2, text="(solo aplica al boton Lift)", fg="gray", bg="#f5f5f5").pack(side=tk.LEFT, padx=8)

frame_estado = tk.Frame(ventana, bg="#f5f5f5")
frame_estado.pack(fill=tk.X, padx=15)
label_estado = tk.Label(frame_estado, text="Listo. Presiona un boton para calcular.", fg="gray", bg="#f5f5f5")
label_estado.pack(side=tk.LEFT)

frame_tabla = tk.Frame(ventana)
frame_tabla.pack(expand=True, fill=tk.BOTH, padx=15, pady=5)

columnas_tabla = ("Item A", "Item B", "Frecuencia / Lift", "Soporte %")
tabla = ttk.Treeview(frame_tabla, columns=columnas_tabla, show="headings")
for col in columnas_tabla:
    tabla.heading(col, text=col)
    tabla.column(col, width=230, anchor="center")

scroll = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tabla.yview)
tabla.configure(yscrollcommand=scroll.set)
tabla.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
scroll.pack(side=tk.RIGHT, fill=tk.Y)

frame_botones = tk.Frame(ventana, pady=12, bg="#f5f5f5")
frame_botones.pack()

botones = [
    ("Apriori",       "APRIORI",  "#bbdefb"),
    ("Vertical",      "VERTICAL", "#c8e6c9"),
    ("Lift",          "LIFT",     "#fff9c4"),
    ("Info Dataset",  "INFO",     "#e1bee7"),
]
for texto, metodo, color in botones:
    tk.Button(frame_botones, text=texto, width=16, bg=color,
              command=lambda m=metodo: ejecutar(m)).pack(side=tk.LEFT, padx=8)

tk.Button(frame_botones, text="Ver Graficas", width=16, bg="#ffe0b2",
          font=("Arial", 9, "bold"), command=abrir_graficas).pack(side=tk.LEFT, padx=8)

ventana.mainloop()