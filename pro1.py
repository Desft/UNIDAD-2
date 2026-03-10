import pandas as pd
import tkinter as tk
from tkinter import ttk
import threading

# cargar el archivo
archivo = "./PROYECTO EXAMEN UNI 2/ventas wal.csv"
datos = pd.read_csv(archivo, sep=";")

# quitar filas que no tienen producto o tienda
datos = datos.dropna(subset=['Item_Identifier', 'Outlet_Identifier'])

# arreglar los nombres del contenido de grasa
datos['Item_Fat_Content'] = datos['Item_Fat_Content'].replace({'LF': 'Low Fat', 'low fat': 'Low Fat', 'reg': 'Regular'})

# convertir a string por si acaso
datos['Item_Identifier'] = datos['Item_Identifier'].astype(str)
datos['Outlet_Identifier'] = datos['Outlet_Identifier'].astype(str)

# usar solo top 50 productos para que no tarde tanto
# con 300 productos eran 44850 pares posibles, con 50 son solo 1225
lista_top50 = datos['Item_Identifier'].value_counts().head(50).index.tolist()

# sacar todos los tipos de items que existen para el combo
todos_los_tipos = sorted(datos['Item_Type'].dropna().unique().tolist())

# pre-calcular el tipo de cada producto una sola vez al inicio
# asi no tenemos que buscar en el dataframe cada vez
cache_tipos = {}
cache_nombres = {}
for codigo in lista_top50:
    filas = datos[datos['Item_Identifier'] == codigo]
    if len(filas) > 0:
        tipo = str(filas.iloc[0]['Item_Type'])
        cache_tipos[codigo] = tipo
        cache_nombres[codigo] = codigo + " (" + tipo + ")"
    else:
        cache_tipos[codigo] = ""
        cache_nombres[codigo] = codigo


# funcion para obtener el nombre completo del producto (usa cache)
def get_nombre(codigo):
    if codigo in cache_nombres:
        return cache_nombres[codigo]
    return codigo


# funcion para obtener el tipo (usa cache)
def get_tipo(codigo):
    if codigo in cache_tipos:
        return cache_tipos[codigo]
    return ""


# funcion que limpia la tabla
def limpiar_tabla():
    for fila in tabla.get_children():
        tabla.delete(fila)


# funcion para insertar resultados ordenados de mayor a menor, max 200
def insertar_resultados_ordenados(lista_resultados):
    lista_ordenada = sorted(lista_resultados, key=lambda x: x[2], reverse=True)
    if len(lista_ordenada) > 200:
        lista_ordenada = lista_ordenada[:200]
    for fila in lista_ordenada:
        tabla.insert("", tk.END, values=fila)


# revisar si el par pasa el filtro de tipo elegido en el combo
def pasa_filtro_tipo(codigo_a, codigo_b):
    tipo_elegido = combo_tipo.get()
    if tipo_elegido == "Todos":
        return True
    tipo_a = get_tipo(codigo_a)
    tipo_b = get_tipo(codigo_b)
    if tipo_elegido == tipo_a or tipo_elegido == tipo_b:
        return True
    return False


# mostrar mensaje de estado arriba
def set_estado(texto):
    ventana.after(0, lambda: label_estado.config(text=texto))


# ---- ALGORITMO APRIORI ----
def correr_apriori(valor_soporte):
    set_estado("Calculando Apriori...")
    limpiar_tabla()

    df = datos[datos['Item_Identifier'].isin(lista_top50)]

    # agrupar por tienda - cada tienda tiene su lista de productos
    transacciones = df.groupby('Outlet_Identifier')['Item_Identifier'].apply(list).to_dict()

    total_tiendas = len(transacciones)
    minimo = total_tiendas * valor_soporte

    # contar los pares
    conteo_pares = {}

    for tienda in transacciones:
        productos_tienda = list(set(transacciones[tienda]))
        productos_tienda.sort()

        i = 0
        while i < len(productos_tienda):
            j = i + 1
            while j < len(productos_tienda):
                par = (productos_tienda[i], productos_tienda[j])
                if par in conteo_pares:
                    conteo_pares[par] = conteo_pares[par] + 1
                else:
                    conteo_pares[par] = 1
                j = j + 1
            i = i + 1

    # filtrar y armar lista de resultados
    resultados = []
    for par in conteo_pares:
        veces = conteo_pares[par]
        if veces >= minimo:
            if not pasa_filtro_tipo(par[0], par[1]):
                continue
            porcentaje = (veces / total_tiendas) * 100
            porcentaje_texto = str(round(porcentaje, 2)) + "%"
            nombre_a = get_nombre(par[0])
            nombre_b = get_nombre(par[1])
            resultados.append((nombre_a, nombre_b, veces, porcentaje_texto))

    ventana.after(0, lambda: insertar_resultados_ordenados(resultados))
    set_estado("Apriori listo - " + str(len(resultados)) + " pares encontrados (mostrando max 200)")


# ---- MINERIA VERTICAL ----
def correr_vertical(valor_soporte):
    set_estado("Calculando Vertical...")
    limpiar_tabla()

    df = datos[datos['Item_Identifier'].isin(lista_top50)]

    # para cada producto, el set de tiendas donde aparece
    tidlists = df.groupby('Item_Identifier')['Outlet_Identifier'].apply(set).to_dict()

    total_outlets = len(df['Outlet_Identifier'].unique())
    minimo = total_outlets * valor_soporte

    lista_items = list(tidlists.keys())
    resultados = []

    i = 0
    while i < len(lista_items):
        j = i + 1
        while j < len(lista_items):
            item_a = lista_items[i]
            item_b = lista_items[j]

            tiendas_comunes = tidlists[item_a] & tidlists[item_b]
            cuantas = len(tiendas_comunes)

            if cuantas >= minimo:
                if pasa_filtro_tipo(item_a, item_b):
                    porcentaje = (cuantas / total_outlets) * 100
                    porcentaje_texto = str(round(porcentaje, 2)) + "%"
                    nombre_a = get_nombre(item_a)
                    nombre_b = get_nombre(item_b)
                    resultados.append((nombre_a, nombre_b, cuantas, porcentaje_texto))

            j = j + 1
        i = i + 1

    ventana.after(0, lambda: insertar_resultados_ordenados(resultados))
    set_estado("Vertical listo - " + str(len(resultados)) + " pares encontrados (mostrando max 200)")


# ---- LIFT ----
def correr_lift(valor_soporte):
    set_estado("Calculando Lift...")
    limpiar_tabla()

    df = datos[datos['Item_Identifier'].isin(lista_top50)]
    transacciones = df.groupby('Outlet_Identifier')['Item_Identifier'].apply(list).to_dict()

    total_tiendas = len(transacciones)

    # frecuencia individual de cada item
    frecuencia_individual = {}
    for tienda in transacciones:
        for item in transacciones[tienda]:
            if item in frecuencia_individual:
                frecuencia_individual[item] = frecuencia_individual[item] + 1
            else:
                frecuencia_individual[item] = 1

    # contar pares
    conteo_pares = {}
    for tienda in transacciones:
        productos_tienda = list(set(transacciones[tienda]))
        productos_tienda.sort()

        i = 0
        while i < len(productos_tienda):
            j = i + 1
            while j < len(productos_tienda):
                par = (productos_tienda[i], productos_tienda[j])
                if par in conteo_pares:
                    conteo_pares[par] = conteo_pares[par] + 1
                else:
                    conteo_pares[par] = 1
                j = j + 1
            i = i + 1

    # leer el operador y el valor del filtro de lift que el usuario puso
    operador_lift = combo_lift_op.get()
    valor_lift_filtro = float(entrada_lift_val.get())

    # calcular lift
    resultados = []
    for par in conteo_pares:
        soporte_par = conteo_pares[par] / total_tiendas
        soporte_a = frecuencia_individual[par[0]] / total_tiendas
        soporte_b = frecuencia_individual[par[1]] / total_tiendas

        lift_valor = soporte_par / (soporte_a * soporte_b)
        lift_redondeado = round(lift_valor, 2)

        # revisar si el lift cumple el operador elegido por el usuario
        pasa_lift = False
        if operador_lift == ">" and lift_redondeado > valor_lift_filtro:
            pasa_lift = True
        elif operador_lift == "<" and lift_redondeado < valor_lift_filtro:
            pasa_lift = True
        elif operador_lift == ">=" and lift_redondeado >= valor_lift_filtro:
            pasa_lift = True
        elif operador_lift == "<=" and lift_redondeado <= valor_lift_filtro:
            pasa_lift = True
        elif operador_lift == "=" and lift_redondeado == valor_lift_filtro:
            pasa_lift = True

        if pasa_lift:
            if pasa_filtro_tipo(par[0], par[1]):
                nombre_a = get_nombre(par[0])
                nombre_b = get_nombre(par[1])
                # poner una etiqueta que explique que significa el lift
                if lift_redondeado > 1.0:
                    etiqueta = "Correlacion positiva"
                elif lift_redondeado < 1.0:
                    etiqueta = "Correlacion negativa"
                else:
                    etiqueta = "Independencia"
                resultados.append((nombre_a, nombre_b, lift_redondeado, etiqueta))

    ventana.after(0, lambda: insertar_resultados_ordenados(resultados))
    set_estado("Lift listo - " + str(len(resultados)) + " pares encontrados (mostrando max 200)")


# ---- INFO DEL DATASET ----
def mostrar_info():
    limpiar_tabla()
    filas_total = len(datos)
    columnas_total = len(datos.columns)
    lista_columnas = list(datos.columns)

    tabla.insert("", tk.END, values=("Filas totales:", filas_total, "", ""))
    tabla.insert("", tk.END, values=("Columnas totales:", columnas_total, "", ""))
    tabla.insert("", tk.END, values=("Tiendas unicas:", len(datos['Outlet_Identifier'].unique()), "", ""))
    tabla.insert("", tk.END, values=("Productos unicos:", len(datos['Item_Identifier'].unique()), "", ""))
    tabla.insert("", tk.END, values=("", "", "", ""))
    tabla.insert("", tk.END, values=("--- COLUMNAS ---", "", "", ""))
    for col in lista_columnas:
        tabla.insert("", tk.END, values=(col, "", "", ""))
    set_estado("Info del dataset cargada")


# (funcion buscar eliminada, ya no hay buscador en la interfaz)


# ---- HILO PARA NO CONGELAR LA VENTANA ----
def ejecutar_en_hilo(metodo):
    soporte_numero = float(entrada_soporte.get())

    def tarea():
        if metodo == "APRIORI":
            correr_apriori(soporte_numero)
        elif metodo == "VERTICAL":
            correr_vertical(soporte_numero)
        elif metodo == "LIFT":
            correr_lift(soporte_numero)
        elif metodo == "INFO":
            mostrar_info()

    hilo = threading.Thread(target=tarea)
    hilo.start()


# ==============================
# GRAFICAS
# ==============================

def abrir_graficas():

    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from tkinter import ttk

    plt.style.use("dark_background")

    # ==============================
    # PREPARAR DATOS
    # ==============================

    df = datos[datos['Item_Identifier'].isin(lista_top50)]

    # PRODUCTOS MAS VENDIDOS
    productos_ventas = (
        df.groupby("Item_Identifier")["Item_Outlet_Sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    # ==============================
    # CONJUNTOS MAS VENDIDOS
    # ==============================

    transacciones = df.groupby("Outlet_Identifier")["Item_Identifier"].apply(list).to_dict()

    conteo_pares = {}

    for tienda in transacciones:

        productos = list(set(transacciones[tienda]))
        productos.sort()

        i = 0
        while i < len(productos):

            j = i + 1

            while j < len(productos):

                par = (productos[i], productos[j])

                conteo_pares[par] = conteo_pares.get(par, 0) + 1

                j += 1

            i += 1

    pares_top = sorted(conteo_pares, key=conteo_pares.get, reverse=True)[:10]

    nombres_pares = []
    valores_pares = []

    for p in pares_top:
        nombres_pares.append(p[0] + " & " + p[1])
        valores_pares.append(conteo_pares[p])

    # ==============================
    # TIPOS DE CORRELACION
    # ==============================

    total_tiendas = len(transacciones)

    frecuencia_individual = {}

    for tienda in transacciones:

        for item in transacciones[tienda]:

            frecuencia_individual[item] = frecuencia_individual.get(item, 0) + 1

    positivos = 0
    negativos = 0
    independientes = 0

    for par in conteo_pares:

        soporte_par = conteo_pares[par] / total_tiendas
        soporte_a = frecuencia_individual[par[0]] / total_tiendas
        soporte_b = frecuencia_individual[par[1]] / total_tiendas

        lift = soporte_par / (soporte_a * soporte_b)

        if lift > 1:
            positivos += 1
        elif lift < 1:
            negativos += 1
        else:
            independientes += 1

    # ==============================
    # GRASA DE PRODUCTOS
    # ==============================

    grasa = datos["Item_Fat_Content"].value_counts()

    # ==============================
    # VENTANA
    # ==============================

    ven = tk.Toplevel(ventana)
    ven.title("Dashboard Analitico - Walmart")
    ven.geometry("1100x700")
    ven.configure(bg="#121212")

    notebook = ttk.Notebook(ven)
    notebook.pack(fill="both", expand=True)

    # =====================================================
    # 1 PRODUCTOS MAS VENDIDOS
    # =====================================================

    tab1 = tk.Frame(notebook, bg="#121212")
    notebook.add(tab1, text="Productos mas vendidos")

    fig1, ax1 = plt.subplots(figsize=(10,6))
    fig1.patch.set_facecolor("#121212")
    ax1.set_facecolor("#1e1e1e")

    ax1.bar(productos_ventas.index,
            productos_ventas.values,
            color="#29b6f6",
            edgecolor="#01579b")

    ax1.set_title("Top 10 Productos mas vendidos", color="white")
    ax1.tick_params(axis='x', rotation=45)

    canvas1 = FigureCanvasTkAgg(fig1, master=tab1)
    canvas1.draw()
    canvas1.get_tk_widget().pack(fill="both", expand=True)

    # =====================================================
    # 2 CONJUNTOS MAS VENDIDOS
    # =====================================================

    tab2 = tk.Frame(notebook, bg="#121212")
    notebook.add(tab2, text="Conjuntos mas vendidos")

    fig2, ax2 = plt.subplots(figsize=(10,6))
    fig2.patch.set_facecolor("#121212")
    ax2.set_facecolor("#1e1e1e")

    ax2.bar(nombres_pares,
            valores_pares,
            color="#00e5ff",
            edgecolor="#00838f")

    ax2.set_title("Top 10 conjuntos de productos", color="white")
    ax2.tick_params(axis='x', rotation=40)

    canvas2 = FigureCanvasTkAgg(fig2, master=tab2)
    canvas2.draw()
    canvas2.get_tk_widget().pack(fill="both", expand=True)

    # =====================================================
    # 3 TIPOS DE CORRELACION
    # =====================================================

    tab3 = tk.Frame(notebook, bg="#121212")
    notebook.add(tab3, text="Tipos de correlacion")

    fig3, ax3 = plt.subplots(figsize=(8,6))
    fig3.patch.set_facecolor("#121212")
    ax3.set_facecolor("#1e1e1e")

    valores = [positivos, independientes, negativos]

    etiquetas = [
        "Correlacion positiva",
        "Independencia",
        "Correlacion negativa"
    ]

    colores = ["#00e676","#ffd54f","#ff5252"]

    ax3.pie(valores,
            labels=etiquetas,
            autopct="%1.1f%%",
            startangle=90,
            colors=colores,
            textprops={"color":"white"},
            shadow=True)

    ax3.set_title("Distribucion de correlaciones")

    canvas3 = FigureCanvasTkAgg(fig3, master=tab3)
    canvas3.draw()
    canvas3.get_tk_widget().pack(fill="both", expand=True)

    # =====================================================
    # 4 GRASA PRODUCTOS
    # =====================================================

    tab4 = tk.Frame(notebook, bg="#121212")
    notebook.add(tab4, text="Grasa en productos")

    fig4, ax4 = plt.subplots(figsize=(8,6))
    fig4.patch.set_facecolor("#121212")
    ax4.set_facecolor("#1e1e1e")

    ax4.pie(grasa.values,
            labels=grasa.index,
            autopct="%1.1f%%",
            startangle=90,
            colors=["#42a5f5","#66bb6a","#ffa726","#ef5350"],
            textprops={"color":"white"},
            shadow=True)

    ax4.set_title("Distribucion de contenido de grasa")

    canvas4 = FigureCanvasTkAgg(fig4, master=tab4)
    canvas4.draw()
    canvas4.get_tk_widget().pack(fill="both", expand=True)


# ==============================
# INTERFAZ GRAFICA
# ==============================

ventana = tk.Tk()
ventana.title("Mineria de Datos - Walmart")
ventana.geometry("1000x700")

# fila 1: soporte y buscador
frame_fila1 = tk.Frame(ventana, pady=6)
frame_fila1.pack(fill=tk.X)

tk.Label(frame_fila1, text="Soporte (0.1 a 1.0):").pack(side=tk.LEFT, padx=5)
entrada_soporte = tk.Entry(frame_fila1, width=8)
entrada_soporte.insert(0, "0.40")
entrada_soporte.pack(side=tk.LEFT, padx=5)

# fila 2: filtro por tipo
frame_fila2 = tk.Frame(ventana, pady=4)
frame_fila2.pack(fill=tk.X)

tk.Label(frame_fila2, text="Filtrar por tipo:").pack(side=tk.LEFT, padx=5)
opciones_tipo = ["Todos"] + todos_los_tipos
combo_tipo = ttk.Combobox(frame_fila2, values=opciones_tipo, width=28, state="readonly")
combo_tipo.current(0)
combo_tipo.pack(side=tk.LEFT, padx=5)

tk.Label(frame_fila2, text="  (top 50 productos, max 200 resultados, ordenado mayor a menor)").pack(side=tk.LEFT, padx=5)

# fila 2b: filtro de lift
frame_fila2b = tk.Frame(ventana, pady=4)
frame_fila2b.pack(fill=tk.X)

tk.Label(frame_fila2b, text="Filtro Lift:  Mostrar pares con lift").pack(side=tk.LEFT, padx=5)

combo_lift_op = ttk.Combobox(frame_fila2b, values=[">", "<", ">=", "<=", "="], width=5, state="readonly")
combo_lift_op.current(2)  # por defecto ">="
combo_lift_op.pack(side=tk.LEFT, padx=3)

entrada_lift_val = tk.Entry(frame_fila2b, width=8)
entrada_lift_val.insert(0, "1.0")
entrada_lift_val.pack(side=tk.LEFT, padx=3)

tk.Label(frame_fila2b, text="   (solo aplica al boton Lift)").pack(side=tk.LEFT, padx=5)

# fila 3: estado
frame_fila3 = tk.Frame(ventana, pady=2)
frame_fila3.pack(fill=tk.X)
label_estado = tk.Label(frame_fila3, text="Listo. Presiona un boton para calcular.", fg="gray")
label_estado.pack(side=tk.LEFT, padx=8)

# tabla
frame_tabla = tk.Frame(ventana)
frame_tabla.pack(expand=True, fill=tk.BOTH, padx=10)

nombres_columnas = ("Item A", "Item B", "Frecuencia / Lift", "Soporte %")
tabla = ttk.Treeview(frame_tabla, columns=nombres_columnas, show='headings')

for col in nombres_columnas:
    tabla.heading(col, text=col)
    tabla.column(col, width=220)

barra_scroll = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tabla.yview)
tabla.configure(yscrollcommand=barra_scroll.set)
tabla.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
barra_scroll.pack(side=tk.RIGHT, fill=tk.Y)

# botones
frame_botones = tk.Frame(ventana, pady=15)
frame_botones.pack()

tk.Button(frame_botones, text="Apriori",      width=18, bg="#e1f5fe", command=lambda: ejecutar_en_hilo("APRIORI")).pack(side=tk.LEFT, padx=8)
tk.Button(frame_botones, text="Vertical",     width=18, bg="#e8f5e9", command=lambda: ejecutar_en_hilo("VERTICAL")).pack(side=tk.LEFT, padx=8)
tk.Button(frame_botones, text="Lift",         width=18, bg="#fff9c4", command=lambda: ejecutar_en_hilo("LIFT")).pack(side=tk.LEFT, padx=8)
tk.Button(frame_botones, text="Info Dataset", width=18, bg="#f3e5f5", command=lambda: ejecutar_en_hilo("INFO")).pack(side=tk.LEFT, padx=8)
tk.Button(frame_botones, text="Ver Graficas", width=18, bg="#ffe0b2", command=abrir_graficas).pack(side=tk.LEFT, padx=8)

ventana.mainloop()