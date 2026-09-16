import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

import customtkinter as ctk
import psycopg2

try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class AppAgenda(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Agenda 3 Patitos")
        self.geometry("1280x760")
        self.minsize(1050, 650)

        self.conn_params = {
            "dbname": "agenda",
            "user": "postgres",
            "password": "postgres",
            "host": "localhost",
            "port": "5432",
        }

        self.usuarios_combo = {}
        self.categorias_combo = {}
        self.categorias_padre_combo = {}

        # Diccionarios agregados
        self.ubicaciones_combo = {}
        self.eventos_combo = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.crear_sidebar()
        self.crear_area_principal()
        self.configurar_estilos()
        self.actualizar_todas_las_tablas()
        # Estaba repetido :P

        if DateEntry is None:
            self.after(500, lambda: messagebox.showwarning(
                "Calendario no instalado",
                "Para usar los selectores de fecha instala:\n\npip install tkcalendar"
            ))

    # -------------------- INFRAESTRUCTURA --------------------

    def obtener_conexion(self):
        conn = psycopg2.connect(**self.conn_params)
        with conn.cursor() as cur:
            cur.execute("SET search_path TO prototipo, public;")
        return conn

    def ejecutar_consulta(self, sql, params=None, fetch=False):
        conn = None
        try:
            conn = self.obtener_conexion()
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall() if fetch else None
            conn.commit()
            return rows
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def configurar_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=30, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

    def crear_treeview(self, parent, columnas, widths):
        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        tree = ttk.Treeview(contenedor, columns=columnas, show="headings")
        for col, width in zip(columnas, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="center")
        scroll_y = ttk.Scrollbar(contenedor, orient="vertical", command=tree.yview)
        scroll_x = ttk.Scrollbar(contenedor, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        contenedor.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)
        return tree

    def seleccionar_modulo(self, nombre):
        self.tabview.set(nombre)
        for modulo, boton in self.botones_nav.items():
            boton.configure(fg_color=("gray75", "gray25") if modulo == nombre else "transparent")

    def crear_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=235, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(
            self.sidebar_frame,
            text="📅 AGENDA 🦆🦆🦆",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(28, 5), sticky="w")

        ctk.CTkLabel(
            self.sidebar_frame,
            text="Gestión de usuarios, categorías, eventos, ubicaciones, disponibilidad y tareas! ^^",
            font=ctk.CTkFont(size=11),
            wraplength=190,
            justify="left"
        ).grid(row=1, column=0, padx=20, pady=(0, 25), sticky="w")

        self.botones_nav = {}
        for i, (nombre, icono) in enumerate([
            ("Usuarios", "👥"),
            ("Categorías", "📁"),
            ("Ubicaciones", "📍"),
            ("Eventos", "📆"),    #No me gustaba ese espacio entonces cambie el emoji :P
            ("Disponibilidad", "📲"),
            ("Tareas", "📄"),
        ], start=2):
            btn = ctk.CTkButton(
                self.sidebar_frame, text=f"{icono}  {nombre}",
                anchor="w", fg_color="transparent",
                command=lambda n=nombre: self.seleccionar_modulo(n)
            )
            btn.grid(row=i, column=0, padx=15, pady=5, sticky="ew")
            self.botones_nav[nombre] = btn

        ctk.CTkButton(
            self.sidebar_frame,
            text="🔄  Recargar datos",
            command=self.actualizar_todas_las_tablas
        ).grid(row=8, column=0, padx=15, pady=(170, 5), sticky="ew")

        ctk.CTkLabel(self.sidebar_frame, text="APARIENCIA", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=11, column=0, padx=20, pady=(10, 5), sticky="w"
        )
        self.option_mode = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["System", "Dark", "Light"],
            command=ctk.set_appearance_mode
        )
        self.option_mode.set("System")
        self.option_mode.grid(row=12, column=0, padx=15, pady=(0, 25), sticky="ew")

    def crear_area_principal(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self.main_container, command=self.al_cambiar_pestana)
        self.tabview.grid(row=0, column=0, sticky="nsew")

        self.tab_usuarios = self.tabview.add("Usuarios")
        self.tab_categorias = self.tabview.add("Categorías")
        self.tab_ubicaciones = self.tabview.add("Ubicaciones")
        self.tab_eventos = self.tabview.add("Eventos")
        self.tab_disponibilidad = self.tabview.add("Disponibilidad")
        self.tab_tareas = self.tabview.add("Tareas")

        self.configurar_pestana_usuarios()
        self.configurar_pestana_categorias()
        self.configurar_pestana_ubicaciones()
        self.configurar_pestana_eventos()
        self.configurar_pestana_disponibilidad()
        self.configurar_pestana_tareas()

        self.seleccionar_modulo("Usuarios")

    def al_cambiar_pestana(self):
        nombre = self.tabview.get()
        if nombre in self.botones_nav:
            for modulo, boton in self.botones_nav.items():
                boton.configure(fg_color=("gray75", "gray25") if modulo == nombre else "transparent")

    def crear_encabezado(self, parent, titulo, descripcion):
        ctk.CTkLabel(parent, text=titulo, font=ctk.CTkFont(size=24, weight="bold")).pack(
            anchor="w", padx=15, pady=(15, 0)
        )
        ctk.CTkLabel(parent, text=descripcion, font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=15, pady=(0, 12)
        )

    # -------------------- USUARIOS --------------------

    def configurar_pestana_usuarios(self):
        self.crear_encabezado(self.tab_usuarios, "Usuarios", "Registra, consulta y administra los usuarios de la agenda.")

        cuerpo = ctk.CTkFrame(self.tab_usuarios, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=5)
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)

        tabla_frame = ctk.CTkFrame(cuerpo)
        tabla_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        form = ctk.CTkScrollableFrame(cuerpo, width=300)
        form.grid(row=0, column=1, sticky="nsew")

        self.tree_usuarios = self.crear_treeview(
            tabla_frame, ("ID", "Nombre", "Apellido", "Registro", "Activo"),
            (70, 160, 160, 160, 80)
        )
        self.tree_usuarios.bind("<<TreeviewSelect>>", self.cargar_usuario_seleccionado)

        ctk.CTkLabel(form, text="Formulario de usuario", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))
        self.entry_nombre = ctk.CTkEntry(form, placeholder_text="Nombre")
        self.entry_nombre.pack(fill="x", padx=10, pady=6)
        self.entry_apellido = ctk.CTkEntry(form, placeholder_text="Apellido")
        self.entry_apellido.pack(fill="x", padx=10, pady=6)

        self.switch_usuario_activo = ctk.CTkSwitch(form, text="Usuario activo")
        self.switch_usuario_activo.select()
        self.switch_usuario_activo.pack(anchor="w", padx=12, pady=10)

        ctk.CTkButton(form, text="➕ Registrar usuario", command=self.agregar_usuario).pack(fill="x", padx=10, pady=(12, 5))
        ctk.CTkButton(form, text="💾 Actualizar seleccionado", command=self.actualizar_usuario).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🧹 Nuevo / Limpiar", command=self.limpiar_form_usuario, fg_color="gray").pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🗑️ Eliminar seleccionado", command=self.eliminar_usuario, fg_color="#b33939", hover_color="#8f2d2d").pack(fill="x", padx=10, pady=5)

    def usuario_seleccionado_id(self):
        sel = self.tree_usuarios.selection()
        return self.tree_usuarios.item(sel[0])["values"][0] if sel else None

    def cargar_usuario_seleccionado(self, _=None):
        sel = self.tree_usuarios.selection()
        if not sel:
            return
        vals = self.tree_usuarios.item(sel[0])["values"]
        self.entry_nombre.delete(0, tk.END); self.entry_nombre.insert(0, vals[1])
        self.entry_apellido.delete(0, tk.END); self.entry_apellido.insert(0, vals[2])
        if vals[4]:
            self.switch_usuario_activo.select()
        else:
            self.switch_usuario_activo.deselect()

    def limpiar_form_usuario(self):
        self.tree_usuarios.selection_remove(self.tree_usuarios.selection())
        self.entry_nombre.delete(0, tk.END)
        self.entry_apellido.delete(0, tk.END)
        self.switch_usuario_activo.select()

    def agregar_usuario(self):
        nombre, apellido = self.entry_nombre.get().strip(), self.entry_apellido.get().strip()
        if not nombre or not apellido:
            return messagebox.showwarning("Campos incompletos", "Indica nombre y apellido.")
        try:
            self.ejecutar_consulta("INSERT INTO usuarios (nombre, apellido, activo) VALUES (%s, %s, %s)",
                                   (nombre, apellido, self.switch_usuario_activo.get() == 1))
            self.limpiar_form_usuario(); self.actualizar_todas_las_tablas()
            messagebox.showinfo("Éxito", "Usuario registrado correctamente.")
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))

    def actualizar_usuario(self):
        uid = self.usuario_seleccionado_id()
        if uid is None:
            return messagebox.showwarning("Selección requerida", "Selecciona un usuario para actualizar.")
        nombre, apellido = self.entry_nombre.get().strip(), self.entry_apellido.get().strip()
        if not nombre or not apellido:
            return messagebox.showwarning("Campos incompletos", "Indica nombre y apellido.")
        try:
            self.ejecutar_consulta("UPDATE usuarios SET nombre=%s, apellido=%s, activo=%s WHERE id_usuario=%s",
                                   (nombre, apellido, self.switch_usuario_activo.get() == 1, uid))
            self.actualizar_todas_las_tablas()
            messagebox.showinfo("Éxito", "Usuario actualizado.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_usuario(self):
        uid = self.usuario_seleccionado_id()
        if uid is None:
            return messagebox.showwarning("Selección requerida", "Selecciona un usuario.")
        if not messagebox.askyesno("Confirmar", "¿Eliminar el usuario seleccionado?"):
            return
        try:
            self.ejecutar_consulta("DELETE FROM usuarios WHERE id_usuario=%s", (uid,))
            self.limpiar_form_usuario(); self.actualizar_todas_las_tablas()
            messagebox.showinfo("Eliminado", "Usuario eliminado.")
        except Exception as e:
            messagebox.showerror("No se pudo eliminar", str(e))

    def cargar_datos_usuarios(self):
        try:
            rows = self.ejecutar_consulta(
                "SELECT id_usuario, nombre, apellido, fecha_registro, activo FROM usuarios ORDER BY nombre, apellido",
                fetch=True
            )
            for item in self.tree_usuarios.get_children(): self.tree_usuarios.delete(item)
            self.usuarios_combo = {}
            for row in rows:
                registro = row[3].strftime("%Y-%m-%d %H:%M") if hasattr(row[3], "strftime") else row[3]
                self.tree_usuarios.insert("", "end", values=(row[0], row[1], row[2], registro, "Sí" if row[4] else "No"))
                etiqueta = f"{row[1]} {row[2]} — #{row[0]}"
                self.usuarios_combo[etiqueta] = row[0]
        except Exception as e:
            print(f"Error cargando usuarios: {e}")

    # -------------------- CATEGORÍAS --------------------

    def configurar_pestana_categorias(self):
        self.crear_encabezado(self.tab_categorias, "Categorías", "Organiza los eventos mediante categorías y subcategorías.")

        cuerpo = ctk.CTkFrame(self.tab_categorias, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=5)
        cuerpo.grid_columnconfigure(0, weight=3); cuerpo.grid_columnconfigure(1, weight=1); cuerpo.grid_rowconfigure(0, weight=1)

        tabla = ctk.CTkFrame(cuerpo); tabla.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        form = ctk.CTkScrollableFrame(cuerpo, width=320); form.grid(row=0, column=1, sticky="nsew")

        self.tree_categorias = self.crear_treeview(tabla, ("ID", "Categoría", "Categoría padre"), (80, 230, 230))
        self.tree_categorias.bind("<<TreeviewSelect>>", self.cargar_categoria_seleccionada)

        ctk.CTkLabel(form, text="Formulario de categoría", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))
        self.entry_cat_nombre = ctk.CTkEntry(form, placeholder_text="Nombre de la categoría")
        self.entry_cat_nombre.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(form, text="Categoría padre").pack(anchor="w", padx=10, pady=(10, 2))
        self.combo_cat_padre = ctk.CTkComboBox(form, values=["Sin categoría padre"], state="readonly")
        self.combo_cat_padre.set("Sin categoría padre")
        self.combo_cat_padre.pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(form, text="➕ Crear categoría", command=self.agregar_categoria).pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkButton(form, text="💾 Actualizar seleccionada", command=self.actualizar_categoria).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🧹 Nueva / Limpiar", command=self.limpiar_form_categoria, fg_color="gray").pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🗑️ Eliminar seleccionada", command=self.eliminar_categoria, fg_color="#b33939", hover_color="#8f2d2d").pack(fill="x", padx=10, pady=5)

    def categoria_seleccionada_id(self):
        sel = self.tree_categorias.selection()
        return self.tree_categorias.item(sel[0])["values"][0] if sel else None

    def cargar_categoria_seleccionada(self, _=None):
        sel = self.tree_categorias.selection()
        if not sel: return
        vals = self.tree_categorias.item(sel[0])["values"]
        self.entry_cat_nombre.delete(0, tk.END); self.entry_cat_nombre.insert(0, vals[1])
        padre = vals[2]
        self.combo_cat_padre.set(padre if padre in self.categorias_padre_combo else "Sin categoría padre")

    def limpiar_form_categoria(self):
        self.tree_categorias.selection_remove(self.tree_categorias.selection())
        self.entry_cat_nombre.delete(0, tk.END); self.combo_cat_padre.set("Sin categoría padre")

    def _padre_id_actual(self):
        valor = self.combo_cat_padre.get()
        return None if valor == "Sin categoría padre" else self.categorias_padre_combo.get(valor)

    def agregar_categoria(self):
        nombre = self.entry_cat_nombre.get().strip()
        if not nombre: return messagebox.showwarning("Campo requerido", "Indica el nombre de la categoría.")
        try:
            self.ejecutar_consulta("INSERT INTO categorias (nombre, id_categoria_padre) VALUES (%s, %s)",
                                   (nombre, self._padre_id_actual()))
            self.limpiar_form_categoria(); self.actualizar_todas_las_tablas()
            messagebox.showinfo("Éxito", "Categoría creada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def actualizar_categoria(self):
        cid = self.categoria_seleccionada_id()
        if cid is None: return messagebox.showwarning("Selección requerida", "Selecciona una categoría.")
        nombre = self.entry_cat_nombre.get().strip(); padre = self._padre_id_actual()
        if not nombre: return messagebox.showwarning("Campo requerido", "Indica el nombre.")
        if padre == cid: return messagebox.showwarning("Relación inválida", "Una categoría no puede ser su propia categoría padre.")
        try:
            self.ejecutar_consulta("UPDATE categorias SET nombre=%s, id_categoria_padre=%s WHERE id_categoria=%s",
                                   (nombre, padre, cid))
            self.actualizar_todas_las_tablas(); messagebox.showinfo("Éxito", "Categoría actualizada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_categoria(self):
        cid = self.categoria_seleccionada_id()
        if cid is None: return messagebox.showwarning("Selección requerida", "Selecciona una categoría.")
        if not messagebox.askyesno("Confirmar", "¿Eliminar la categoría seleccionada?"): return
        try:
            self.ejecutar_consulta("DELETE FROM categorias WHERE id_categoria=%s", (cid,))
            self.limpiar_form_categoria(); self.actualizar_todas_las_tablas()
            messagebox.showinfo("Eliminado", "Categoría eliminada.")
        except Exception as e:
            messagebox.showerror("No se pudo eliminar", str(e))

    def cargar_datos_categorias(self):
        try:
            rows = self.ejecutar_consulta("""
                SELECT c.id_categoria, c.nombre, p.nombre
                FROM categorias c
                LEFT JOIN categorias p ON p.id_categoria = c.id_categoria_padre
                ORDER BY c.nombre
            """, fetch=True)
            ids = self.ejecutar_consulta("SELECT id_categoria, nombre FROM categorias ORDER BY nombre", fetch=True)

            for item in self.tree_categorias.get_children(): self.tree_categorias.delete(item)
            self.categorias_combo = {}
            self.categorias_padre_combo = {}
            for cid, nombre in ids:
                etiqueta = f"{nombre} — #{cid}"
                self.categorias_combo[etiqueta] = cid
                self.categorias_padre_combo[etiqueta] = cid
            for row in rows:
                padre = "Sin categoría padre"
                if row[2] is not None:
                    # Buscar etiqueta completa del padre
                    for etiqueta, cid in self.categorias_padre_combo.items():
                        if etiqueta.startswith(f"{row[2]} —"):
                            padre = etiqueta; break
                self.tree_categorias.insert("", "end", values=(row[0], row[1], padre))

            valores_padre = ["Sin categoría padre"] + list(self.categorias_padre_combo.keys())
            self.combo_cat_padre.configure(values=valores_padre)
            if self.combo_cat_padre.get() not in valores_padre:
                self.combo_cat_padre.set("Sin categoría padre")
        except Exception as e:
            print(f"Error cargando categorías: {e}")

    # -------------------- UBICACIONES --------------------
    def configurar_pestana_ubicaciones(self):
        self.crear_encabezado(self.tab_ubicaciones, "Ubicaciones", "Administra los recintos físicos y analiza su nivel de ocupación.")
        cuerpo = ctk.CTkFrame(self.tab_ubicaciones, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=5)
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)
        
        panel_tablas = ctk.CTkFrame(cuerpo, fg_color="transparent")
        panel_tablas.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panel_tablas.grid_columnconfigure(0, weight=1)
        panel_tablas.grid_rowconfigure(0, weight=2)
        panel_tablas.grid_rowconfigure(2, weight=1)

        frame_tree_ubicaciones = ctk.CTkFrame(panel_tablas, fg_color="transparent")
        frame_tree_ubicaciones.grid(row=0, column=0, sticky="nsew")
        self.tree_ubicaciones = self.crear_treeview(frame_tree_ubicaciones, ("ID", "Nombre", "Dirección", "Ciudad", "Capacidad"), (50, 150, 150, 100, 80))
        self.tree_ubicaciones.bind("<<TreeviewSelect>>", self.cargar_ubicacion_seleccionada)

        ctk.CTkLabel(panel_tablas, text="Reporte de Ocupación de Recintos", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", pady=(10, 5))

        frame_tree_reporte_ubicaciones = ctk.CTkFrame(panel_tablas, fg_color="transparent")
        frame_tree_reporte_ubicaciones.grid(row=2, column=0, sticky="nsew")
        self.tree_reporte_ubicaciones = self.crear_treeview(frame_tree_reporte_ubicaciones, ("ID", "Recinto", "Capacidad", "Total Eventos"), (50, 200, 100, 100))


        form = ctk.CTkScrollableFrame(cuerpo, width=300)
        form.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(form, text="Formulario de Ubicación", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))
        
        self.entry_ub_nombre = ctk.CTkEntry(form, placeholder_text="Nombre del recinto")
        self.entry_ub_nombre.pack(fill="x", padx=10, pady=6)
        self.entry_ub_direccion = ctk.CTkEntry(form, placeholder_text="Dirección física")
        self.entry_ub_direccion.pack(fill="x", padx=10, pady=6)
        self.entry_ub_ciudad = ctk.CTkEntry(form, placeholder_text="Ciudad")
        self.entry_ub_ciudad.pack(fill="x", padx=10, pady=6)
        self.entry_ub_capacidad = ctk.CTkEntry(form, placeholder_text="Capacidad (número)")
        self.entry_ub_capacidad.pack(fill="x", padx=10, pady=6)
        
        ctk.CTkButton(form, text="➕ Registrar ubicación", command=self.agregar_ubicacion).pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkButton(form, text="💾 Actualizar seleccionada", command=self.actualizar_ubicacion).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🧹 Nuevo / Limpiar", command=self.limpiar_form_ubicacion, fg_color="gray").pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🗑️ Eliminar seleccionada", command=self.eliminar_ubicacion, fg_color="#b33939", hover_color="#8f2d2d").pack(fill="x", padx=10, pady=5)

    def limpiar_form_ubicacion(self):
        self.tree_ubicaciones.selection_remove(self.tree_ubicaciones.selection())
        for widget in (self.entry_ub_nombre, self.entry_ub_direccion, self.entry_ub_ciudad, self.entry_ub_capacidad):
            widget.delete(0, tk.END)

    def ubicacion_seleccionada_id(self):
        sel = self.tree_ubicaciones.selection()
        return self.tree_ubicaciones.item(sel[0])["values"][0] if sel else None

    def cargar_ubicacion_seleccionada(self, _=None):
        sel = self.tree_ubicaciones.selection()
        if not sel: return
        vals = self.tree_ubicaciones.item(sel[0])["values"]
        self.limpiar_form_ubicacion()
        self.entry_ub_nombre.insert(0, vals[1])
        self.entry_ub_direccion.insert(0, vals[2])
        self.entry_ub_ciudad.insert(0, vals[3])
        self.entry_ub_capacidad.insert(0, vals[4])

    def agregar_ubicacion(self):
        nombre = self.entry_ub_nombre.get().strip()
        if not nombre:
            return messagebox.showwarning("Campo requerido", "Indica el nombre del recinto.")
        try:
            self.ejecutar_consulta(
                "INSERT INTO ubicaciones (nombre, direccion, ciudad, capacidad) VALUES (%s, %s, %s, %s)",
                (nombre, self.entry_ub_direccion.get(), self.entry_ub_ciudad.get(), self.entry_ub_capacidad.get())
            )
            self.limpiar_form_ubicacion()
            self.cargar_datos_ubicaciones()
            messagebox.showinfo("Éxito", "Ubicación registrada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def actualizar_ubicacion(self):
        uid = self.ubicacion_seleccionada_id()
        if uid is None:
            return messagebox.showwarning("Selección requerida", "Selecciona una ubicación para actualizar.")
        nombre = self.entry_ub_nombre.get().strip()
        if not nombre:
            return messagebox.showwarning("Campo requerido", "Indica el nombre del recinto.")
        try:
            self.ejecutar_consulta(
                "UPDATE ubicaciones SET nombre=%s, direccion=%s, ciudad=%s, capacidad=%s WHERE id_ubicacion=%s",
                (nombre, self.entry_ub_direccion.get(), self.entry_ub_ciudad.get(), self.entry_ub_capacidad.get(), uid)
            )
            self.cargar_datos_ubicaciones()
            messagebox.showinfo("Éxito", "Ubicación actualizada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_ubicacion(self):
        uid = self.ubicacion_seleccionada_id()
        if uid is None:
            return messagebox.showwarning("Selección requerida", "Selecciona una ubicación.")
        if not messagebox.askyesno("Confirmar", "¿Eliminar la ubicación seleccionada?"):
            return
        try:
            self.ejecutar_consulta("DELETE FROM ubicaciones WHERE id_ubicacion=%s", (uid,))
            self.limpiar_form_ubicacion()
            self.cargar_datos_ubicaciones()
            messagebox.showinfo("Eliminado", "Ubicación eliminada.")
        except Exception as e:
            messagebox.showerror("No se pudo eliminar", str(e))

    def cargar_datos_ubicaciones(self):
        try:
            for item in self.tree_ubicaciones.get_children():
                self.tree_ubicaciones.delete(item)
            rows = self.ejecutar_consulta(
                "SELECT id_ubicacion, nombre, direccion, ciudad, capacidad FROM ubicaciones ORDER BY nombre",
                fetch=True
            )
            self.ubicaciones_combo = {}
            for r in rows:
                self.tree_ubicaciones.insert("", "end", values=r)
                self.ubicaciones_combo[f"{r[1]} - #{r[0]}"] = r[0]

            for item in self.tree_reporte_ubicaciones.get_children():
                self.tree_reporte_ubicaciones.delete(item)
            rep_rows = self.ejecutar_consulta(
                "SELECT id_ubicacion, nombre, capacidad, total_eventos_programados "
                "FROM vista_ocupacion_ubicaciones ORDER BY total_eventos_programados DESC",
                fetch=True
            )
            for r in rep_rows:
                self.tree_reporte_ubicaciones.insert("", "end", values=r)

            if hasattr(self, 'combo_ev_ubicacion'):
                self.combo_ev_ubicacion.configure(values=["Sin ubicación"] + list(self.ubicaciones_combo.keys()))
        except Exception as e:
            print(f"Error cargando ubicaciones: {e}")


    # -------------------- EVENTOS --------------------

    def configurar_pestana_eventos(self):
        self.crear_encabezado(self.tab_eventos, "Eventos", "Programa eventos seleccionando usuarios, categorías, fechas y horas.")

        cuerpo = ctk.CTkFrame(self.tab_eventos, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=5)
        cuerpo.grid_columnconfigure(0, weight=3); cuerpo.grid_columnconfigure(1, weight=1); cuerpo.grid_rowconfigure(0, weight=1)

        tabla = ctk.CTkFrame(cuerpo); tabla.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        form = ctk.CTkScrollableFrame(cuerpo, width=350); form.grid(row=0, column=1, sticky="nsew")

        self.tree_eventos = self.crear_treeview(
            tabla, ("ID", "Propietario", "Categoría","Ubicacion", "Título", "Inicio", "Fin"),
            (70, 170, 150, 220, 150, 150)
        )
        self.tree_eventos.bind("<<TreeviewSelect>>", self.cargar_evento_seleccionado)

        ctk.CTkLabel(form, text="Formulario de evento", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 12))

        self.entry_ev_titulo = ctk.CTkEntry(form, placeholder_text="Título del evento")
        self.entry_ev_titulo.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(form, text="Propietario").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_ev_usuario = ctk.CTkComboBox(form, values=["Seleccione un usuario"], state="readonly")
        self.combo_ev_usuario.set("Seleccione un usuario")
        self.combo_ev_usuario.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(form, text="Categoría").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_ev_categoria = ctk.CTkComboBox(form, values=["Seleccione una categoría"], state="readonly")
        self.combo_ev_categoria.set("Seleccione una categoría")
        self.combo_ev_categoria.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(form, text="Ubicación").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_ev_ubicacion = ctk.CTkComboBox(form, values=["Sin ubicación"], state="readonly")
        self.combo_ev_ubicacion.set("Sin ubicación")
        self.combo_ev_ubicacion.pack(fill="x", padx=10, pady=4)


        ctk.CTkLabel(form, text="Inicio").pack(anchor="w", padx=10, pady=(10, 2))
        fila_inicio = ctk.CTkFrame(form, fg_color="transparent"); fila_inicio.pack(fill="x", padx=10)
        self.fecha_inicio = self.crear_selector_fecha(fila_inicio)
        self.fecha_inicio.pack(side="left", fill="x", expand=True)
        self.hora_inicio = ctk.CTkEntry(fila_inicio, placeholder_text="HH:MM", width=75)
        self.hora_inicio.pack(side="left", padx=(6, 0))

        ctk.CTkLabel(form, text="Fin").pack(anchor="w", padx=10, pady=(10, 2))
        fila_fin = ctk.CTkFrame(form, fg_color="transparent"); fila_fin.pack(fill="x", padx=10)
        self.fecha_fin = self.crear_selector_fecha(fila_fin)
        self.fecha_fin.pack(side="left", fill="x", expand=True)
        self.hora_fin = ctk.CTkEntry(fila_fin, placeholder_text="HH:MM", width=75)
        self.hora_fin.pack(side="left", padx=(6, 0))

        ctk.CTkButton(form, text="➕ Crear evento", command=self.agregar_evento).pack(fill="x", padx=10, pady=(16, 5))
        ctk.CTkButton(form, text="💾 Actualizar seleccionado", command=self.actualizar_evento).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🧹 Nuevo / Limpiar", command=self.limpiar_form_evento, fg_color="gray").pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🗑️ Eliminar seleccionado", command=self.eliminar_evento, fg_color="#b33939", hover_color="#8f2d2d").pack(fill="x", padx=10, pady=5)

        self.limpiar_form_evento()

    def crear_selector_fecha(self, parent):
        if DateEntry is not None:
            return DateEntry(parent, date_pattern="yyyy-mm-dd", font=("Arial", 10))
        return ttk.Entry(parent)

    def obtener_fecha(self, widget):
        if DateEntry is not None:
            return widget.get_date().strftime("%Y-%m-%d")
        return widget.get().strip()

    def establecer_fecha(self, widget, valor):
        fecha = valor.date() if hasattr(valor, "date") else datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
        if DateEntry is not None:
            widget.set_date(fecha)
        else:
            widget.delete(0, tk.END); widget.insert(0, fecha.strftime("%Y-%m-%d"))

    def evento_seleccionado_id(self):
        sel = self.tree_eventos.selection()
        return self.tree_eventos.item(sel[0])["values"][0] if sel else None

    def cargar_evento_seleccionado(self, _=None):
        sel = self.tree_eventos.selection()
        if not sel: return
        vals = self.tree_eventos.item(sel[0])["values"]
        self.entry_ev_titulo.delete(0, tk.END); self.entry_ev_titulo.insert(0, vals[3])
        self.combo_ev_usuario.set(vals[1])
        self.combo_ev_categoria.set(vals[2])
        try:
            ini = datetime.strptime(str(vals[4]), "%Y-%m-%d %H:%M")
            fin = datetime.strptime(str(vals[5]), "%Y-%m-%d %H:%M")
            self.establecer_fecha(self.fecha_inicio, ini)
            self.establecer_fecha(self.fecha_fin, fin)
            self.hora_inicio.delete(0, tk.END); self.hora_inicio.insert(0, ini.strftime("%H:%M"))
            self.hora_fin.delete(0, tk.END); self.hora_fin.insert(0, fin.strftime("%H:%M"))
        except ValueError:
            pass

    def limpiar_form_evento(self):
        self.tree_eventos.selection_remove(self.tree_eventos.selection())
        self.entry_ev_titulo.delete(0, tk.END)
        self.combo_ev_usuario.set("Seleccione un usuario")
        self.combo_ev_categoria.set("Seleccione una categoría")
        self.combo_ev_ubicacion.set("Sin ubicación")
        hoy = datetime.now()
        self.establecer_fecha(self.fecha_inicio, hoy); self.establecer_fecha(self.fecha_fin, hoy)
        self.hora_inicio.delete(0, tk.END); self.hora_inicio.insert(0, "09:00")
        self.hora_fin.delete(0, tk.END); self.hora_fin.insert(0, "10:00")

    def datos_evento_formulario(self):
        titulo = self.entry_ev_titulo.get().strip()
        usuario = self.usuarios_combo.get(self.combo_ev_usuario.get())
        categoria = self.categorias_combo.get(self.combo_ev_categoria.get())
        ubicacion = self.ubicaciones_combo.get(self.combo_ev_ubicacion.get())
        try:
            inicio = datetime.strptime(f"{self.obtener_fecha(self.fecha_inicio)} {self.hora_inicio.get().strip()}", "%Y-%m-%d %H:%M")
            fin = datetime.strptime(f"{self.obtener_fecha(self.fecha_fin)} {self.hora_fin.get().strip()}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("La hora debe tener formato HH:MM, por ejemplo 09:30.")
        if not titulo or usuario is None or categoria is None:
            raise ValueError("Complete todos los campos para crear el evento.")
        if fin <= inicio:
            raise ValueError("La fecha y hora de finalización deben ser posteriores al inicio.")
        return usuario, categoria, titulo, inicio, fin

    def agregar_evento(self):
        try:
            datos = self.datos_evento_formulario()
            self.ejecutar_consulta("""
                INSERT INTO eventos
                (id_usuario_propietario, id_categoria, titulo, fecha_inicio, fecha_fin)
                VALUES (%s, %s, %s, %s, %s)
            """, datos)
            self.limpiar_form_evento(); self.cargar_datos_eventos()
            messagebox.showinfo("Éxito", "Evento creado correctamente.")
        except Exception as e:
            messagebox.showerror("No se pudo crear el evento", str(e))

    def actualizar_evento(self):
        eid = self.evento_seleccionado_id()
        if eid is None: return messagebox.showwarning("Selección requerida", "Selecciona un evento.")
        try:
            usuario, categoria, titulo, inicio, fin = self.datos_evento_formulario()
            self.ejecutar_consulta("""
                UPDATE eventos SET id_usuario_propietario=%s, id_categoria=%s,
                titulo=%s, fecha_inicio=%s, fecha_fin=%s WHERE id_evento=%s
            """, (usuario, categoria, titulo, inicio, fin, eid))
            self.cargar_datos_eventos(); messagebox.showinfo("Éxito", "Evento actualizado.")
        except Exception as e:
            messagebox.showerror("No se pudo actualizar", str(e))

    def eliminar_evento(self):
        eid = self.evento_seleccionado_id()
        if eid is None: return messagebox.showwarning("Selección requerida", "Selecciona un evento.")
        if not messagebox.askyesno("Confirmar", "¿Eliminar el evento seleccionado?"): return
        try:
            self.ejecutar_consulta("DELETE FROM eventos WHERE id_evento=%s", (eid,))
            self.limpiar_form_evento(); self.cargar_datos_eventos()
            messagebox.showinfo("Eliminado", "Evento eliminado.")
        except Exception as e:
            messagebox.showerror("No se pudo eliminar", str(e))

    def cargar_datos_eventos(self):
        try:
            rows = self.ejecutar_consulta("""
                SELECT e.id_evento, u.id_usuario, u.nombre, u.apellido,
                       c.id_categoria, c.nombre, e.titulo, e.fecha_inicio, e.fecha_fin
                FROM eventos e
                JOIN usuarios u ON u.id_usuario = e.id_usuario_propietario
                JOIN categorias c ON c.id_categoria = e.id_categoria
                ORDER BY e.fecha_inicio DESC
            """, fetch=True)
            for item in self.tree_eventos.get_children(): self.tree_eventos.delete(item)
            self.eventos_combo = {}
            for row in rows:
                usuario = f"{row[2]} {row[3]} — #{row[1]}"
                categoria = f"{row[5]} — #{row[4]}"
                inicio = row[7].strftime("%Y-%m-%d %H:%M") if hasattr(row[7], "strftime") else row[7]
                fin = row[8].strftime("%Y-%m-%d %H:%M") if hasattr(row[8], "strftime") else row[8]
                self.tree_eventos.insert("", "end", values=(row[0], usuario, categoria, row[6], inicio, fin))
                self.eventos_combo[f"{row[6]} — #{row[0]}"] = row[0]

            valores_u = ["Seleccione un usuario"] + list(self.usuarios_combo.keys())
            valores_c = ["Seleccione una categoría"] + list(self.categorias_combo.keys())
            self.combo_ev_usuario.configure(values=valores_u)
            self.combo_ev_categoria.configure(values=valores_c)

            if hasattr(self, 'combo_tar_evento'):
                self.combo_tar_evento.configure(values=["Seleccione evento"] + list(self.eventos_combo.keys()))

        except Exception as e:
            print(f"Error cargando eventos: {e}")

    # -------------------- DISPONIBILIDAD --------------------
    def configurar_pestana_disponibilidad(self):
        self.crear_encabezado(self.tab_disponibilidad, "Disponibilidad", "Gestiona los intervalos libres y ocupados de usuarios.")
        cuerpo = ctk.CTkFrame(self.tab_disponibilidad, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=5)
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)
        
        tabla_frame = ctk.CTkFrame(cuerpo)
        tabla_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.tree_dispo = self.crear_treeview(tabla_frame, ("ID", "Usuario", "Fecha", "Inicio", "Fin", "Estado"), (50, 180, 100, 80, 80, 100))
        self.tree_dispo.bind("<<TreeviewSelect>>", self.cargar_dispo_seleccionada)
        
        form = ctk.CTkScrollableFrame(cuerpo, width=300)
        form.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(form, text="Registrar Disponibilidad", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))

        ctk.CTkLabel(form, text="Usuario").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_disp_usuario = ctk.CTkComboBox(form, values=["Seleccione un usuario"], state="readonly")
        self.combo_disp_usuario.set("Seleccione un usuario")
        self.combo_disp_usuario.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(form, text="Fecha").pack(anchor="w", padx=10, pady=(8, 2))
        self.disp_fecha = self.crear_selector_fecha(form)
        self.disp_fecha.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(form, text="Hora Inicio (HH:MM)").pack(anchor="w", padx=10, pady=(8, 2))
        self.entry_disp_inicio = ctk.CTkEntry(form, placeholder_text="08:00")
        self.entry_disp_inicio.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(form, text="Hora Fin (HH:MM)").pack(anchor="w", padx=10, pady=(8, 2))
        self.entry_disp_fin = ctk.CTkEntry(form, placeholder_text="12:00")
        self.entry_disp_fin.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(form, text="Estado").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_disp_estado = ctk.CTkComboBox(form, values=["disponible", "ocupado", "no disponible"], state="readonly")
        self.combo_disp_estado.set("disponible")
        self.combo_disp_estado.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(form, text="➕ Registrar franja", command=self.agregar_dispo).pack(fill="x", padx=10, pady=(16, 5))
        ctk.CTkButton(form, text="💾 Actualizar seleccionada", command=self.actualizar_dispo).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🧹 Nuevo / Limpiar", command=self.limpiar_form_dispo, fg_color="gray").pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🗑️ Eliminar seleccionada", command=self.eliminar_dispo, fg_color="#b33939", hover_color="#8f2d2d").pack(fill="x", padx=10, pady=5)

    def limpiar_form_dispo(self):
        self.tree_dispo.selection_remove(self.tree_dispo.selection())
        self.combo_disp_usuario.set("Seleccione un usuario")
        self.combo_disp_estado.set("disponible")
        self.entry_disp_inicio.delete(0, tk.END)
        self.entry_disp_fin.delete(0, tk.END)

    def dispo_seleccionada_id(self):
        sel = self.tree_dispo.selection()
        return self.tree_dispo.item(sel[0])["values"][0] if sel else None
        
    def cargar_dispo_seleccionada(self, _=None):
        sel = self.tree_dispo.selection()
        if not sel: return
        v = self.tree_dispo.item(sel[0])["values"]
        self.limpiar_form_dispo()
        self.combo_disp_usuario.set(v[1])
        self.establecer_fecha(self.disp_fecha, datetime.strptime(v[2], "%Y-%m-%d"))
        self.entry_disp_inicio.insert(0, str(v[3])[:5])
        self.entry_disp_fin.insert(0, str(v[4])[:5])
        self.combo_disp_estado.set(v[5])

    def agregar_dispo(self):
        usr = self.usuarios_combo.get(self.combo_disp_usuario.get())
        inicio, fin = self.entry_disp_inicio.get().strip(), self.entry_disp_fin.get().strip()
        if not usr:
            return messagebox.showwarning("Campo requerido", "Selecciona un usuario.")
        if not inicio or not fin:
            return messagebox.showwarning("Campos incompletos", "Indica la hora de inicio y de fin.")
        try:
            self.ejecutar_consulta(
                "INSERT INTO disponibilidad_usuarios (id_usuario, fecha, hora_inicio, hora_fin, estado) "
                "VALUES (%s, %s, %s, %s, %s)",
                (usr, self.obtener_fecha(self.disp_fecha), inicio, fin, self.combo_disp_estado.get())
            )
            self.limpiar_form_dispo()
            self.cargar_datos_disponibilidad()
            messagebox.showinfo("Éxito", "Disponibilidad registrada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def actualizar_dispo(self):
        did = self.dispo_seleccionada_id()
        if did is None:
            return messagebox.showwarning("Selección requerida", "Selecciona una franja para actualizar.")
        usr = self.usuarios_combo.get(self.combo_disp_usuario.get())
        inicio, fin = self.entry_disp_inicio.get().strip(), self.entry_disp_fin.get().strip()
        if not usr:
            return messagebox.showwarning("Campo requerido", "Selecciona un usuario.")
        if not inicio or not fin:
            return messagebox.showwarning("Campos incompletos", "Indica la hora de inicio y de fin.")
        try:
            self.ejecutar_consulta(
                "UPDATE disponibilidad_usuarios SET id_usuario=%s, fecha=%s, hora_inicio=%s, hora_fin=%s, estado=%s "
                "WHERE id_disponibilidad=%s",
                (usr, self.obtener_fecha(self.disp_fecha), inicio, fin, self.combo_disp_estado.get(), did)
            )
            self.cargar_datos_disponibilidad()
            messagebox.showinfo("Éxito", "Disponibilidad actualizada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_dispo(self):
        did = self.dispo_seleccionada_id()
        if did is None:
            return messagebox.showwarning("Selección requerida", "Selecciona una franja de disponibilidad.")
        if not messagebox.askyesno("Confirmar", "¿Eliminar la franja de disponibilidad seleccionada?"):
            return
        try:
            self.ejecutar_consulta("DELETE FROM disponibilidad_usuarios WHERE id_disponibilidad=%s", (did,))
            self.limpiar_form_dispo()
            self.cargar_datos_disponibilidad()
            messagebox.showinfo("Eliminado", "Disponibilidad eliminada.")
        except Exception as e:
            messagebox.showerror("No se pudo eliminar", str(e))

    def cargar_datos_disponibilidad(self):
        try:
            for item in self.tree_dispo.get_children():
                self.tree_dispo.delete(item)
            rows = self.ejecutar_consulta(
                "SELECT id_usuario, nombre_completo, fecha, hora_inicio, hora_fin, estado "
                "FROM vista_intervalos_disponibilidad ORDER BY fecha DESC",
                fetch=True
            )
            for r in rows:
                self.tree_dispo.insert("", "end", values=(r[0], f"{r[1]} - #{r[0]}", r[2], r[3], r[4], r[5]))

            if hasattr(self, 'combo_disp_usuario'):
                self.combo_disp_usuario.configure(values=["Seleccione un usuario"] + list(self.usuarios_combo.keys()))
        except Exception as e:
            print(f"Error cargando disponibilidad: {e}")

    # -------------------- TAREAS --------------------
    def configurar_pestana_tareas(self):
        self.crear_encabezado(self.tab_tareas, "Tareas por Evento", "Asigna tareas y verifica los vencimientos operativos.")
        cuerpo = ctk.CTkFrame(self.tab_tareas, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=5)
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)
        
        panel_tablas = ctk.CTkFrame(cuerpo, fg_color="transparent")
        panel_tablas.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panel_tablas.grid_columnconfigure(0, weight=1)
        panel_tablas.grid_rowconfigure(0, weight=2)
        panel_tablas.grid_rowconfigure(2, weight=1)

        frame_tree_tareas = ctk.CTkFrame(panel_tablas, fg_color="transparent")
        frame_tree_tareas.grid(row=0, column=0, sticky="nsew")
        self.tree_tareas = self.crear_treeview(frame_tree_tareas, ("ID", "Evento", "Responsable", "Título", "Estado", "Límite"), (40, 120, 120, 150, 80, 120))
        self.tree_tareas.bind("<<TreeviewSelect>>", self.cargar_tarea_seleccionada)
                                                    # (RF-17)
        ctk.CTkLabel(panel_tablas, text="Reporte de Tareas Vencidas", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", pady=(10, 5))

        frame_tree_vencidas = ctk.CTkFrame(panel_tablas, fg_color="transparent")
        frame_tree_vencidas.grid(row=2, column=0, sticky="nsew")
        self.tree_vencidas = self.crear_treeview(frame_tree_vencidas, ("ID", "Evento", "Responsable", "Título", "Estado", "Límite"), (40, 120, 120, 150, 80, 120))

        form = ctk.CTkScrollableFrame(cuerpo, width=300)
        form.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(form, text="Formulario de Tarea", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))

        ctk.CTkLabel(form, text="Evento").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_tar_evento = ctk.CTkComboBox(form, values=["Seleccione evento"], state="readonly")
        self.combo_tar_evento.set("Seleccione evento")
        self.combo_tar_evento.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(form, text="Responsable").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_tar_resp = ctk.CTkComboBox(form, values=["Seleccione responsable"], state="readonly")
        self.combo_tar_resp.set("Seleccione responsable")
        self.combo_tar_resp.pack(fill="x", padx=10, pady=4)

        self.entry_tar_titulo = ctk.CTkEntry(form, placeholder_text="Título de tarea")
        self.entry_tar_titulo.pack(fill="x", padx=10, pady=4)
        self.entry_tar_desc = ctk.CTkEntry(form, placeholder_text="Descripción breve")
        self.entry_tar_desc.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(form, text="Prioridad").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_tar_prio = ctk.CTkComboBox(form, values=["Alta", "Media", "Baja"], state="readonly")
        self.combo_tar_prio.set("Media")
        self.combo_tar_prio.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(form, text="Estado").pack(anchor="w", padx=10, pady=(8, 2))
        self.combo_tar_estado = ctk.CTkComboBox(form, values=["Pendiente", "En progreso", "Completada", "Cancelada"], state="readonly")
        self.combo_tar_estado.set("Pendiente")
        self.combo_tar_estado.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(form, text="Fecha y Hora Límite").pack(anchor="w", padx=10, pady=(8, 2))
        self.tar_fecha = self.crear_selector_fecha(form)
        self.tar_fecha.pack(fill="x", padx=10, pady=2)
        self.entry_tar_hora = ctk.CTkEntry(form, placeholder_text="HH:MM")
        self.entry_tar_hora.pack(fill="x", padx=10, pady=2)

        ctk.CTkButton(form, text="➕ Registrar tarea", command=self.agregar_tarea).pack(fill="x", padx=10, pady=(16, 5))
        ctk.CTkButton(form, text="💾 Actualizar seleccionada", command=self.actualizar_tarea).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🧹 Nuevo / Limpiar", command=self.limpiar_form_tarea, fg_color="gray").pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(form, text="🗑️ Eliminar seleccionada", command=self.eliminar_tarea, fg_color="#b33939", hover_color="#8f2d2d").pack(fill="x", padx=10, pady=5)

    def limpiar_form_tarea(self):
        self.tree_tareas.selection_remove(self.tree_tareas.selection())
        self.combo_tar_evento.set("Seleccione evento")
        self.combo_tar_resp.set("Seleccione responsable")
        self.entry_tar_titulo.delete(0, tk.END)
        self.entry_tar_desc.delete(0, tk.END)
        self.entry_tar_hora.delete(0, tk.END)
        self.combo_tar_prio.set("Media")
        self.combo_tar_estado.set("Pendiente")

    def tarea_seleccionada_id(self):
        sel = self.tree_tareas.selection()
        return self.tree_tareas.item(sel[0])["values"][0] if sel else None

    def cargar_tarea_seleccionada(self, _=None):
        tid = self.tarea_seleccionada_id()
        if not tid: return
        r = self.ejecutar_consulta(
            "SELECT id_evento, id_responsable, titulo, descripcion, prioridad, estado, fecha_limite "
            "FROM tareas WHERE id_tarea=%s",
            (tid,), fetch=True
        )[0]
        self.limpiar_form_tarea()
        ev_key = next((k for k, v in self.eventos_combo.items() if v == r[0]), "Seleccione evento")
        resp_key = next((k for k, v in self.usuarios_combo.items() if v == r[1]), "Seleccione responsable")
        self.combo_tar_evento.set(ev_key)
        self.combo_tar_resp.set(resp_key)
        self.entry_tar_titulo.insert(0, r[2])
        self.entry_tar_desc.insert(0, r[3])
        self.combo_tar_prio.set(r[4])
        self.combo_tar_estado.set(r[5])
        self.establecer_fecha(self.tar_fecha, r[6])
        self.entry_tar_hora.insert(0, r[6].strftime("%H:%M") if hasattr(r[6], "strftime") else str(r[6])[11:16])

    def agregar_tarea(self):
        ev = self.eventos_combo.get(self.combo_tar_evento.get())
        resp = self.usuarios_combo.get(self.combo_tar_resp.get())
        titulo = self.entry_tar_titulo.get().strip()
        if not ev or not resp:
            return messagebox.showwarning("Campos incompletos", "Selecciona evento y responsable.")
        if not titulo:
            return messagebox.showwarning("Campo requerido", "Indica el título de la tarea.")
        flimite = f"{self.obtener_fecha(self.tar_fecha)} {self.entry_tar_hora.get().strip()}"
        try:
            self.ejecutar_consulta(
                "INSERT INTO tareas (id_evento, id_responsable, titulo, descripcion, prioridad, estado, fecha_limite) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (ev, resp, titulo, self.entry_tar_desc.get(), self.combo_tar_prio.get(), self.combo_tar_estado.get(), flimite)
            )
            self.limpiar_form_tarea()
            self.cargar_datos_tareas()
            messagebox.showinfo("Éxito", "Tarea registrada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def actualizar_tarea(self):
        tid = self.tarea_seleccionada_id()
        if tid is None:
            return messagebox.showwarning("Selección requerida", "Selecciona una tarea para actualizar.")
        ev = self.eventos_combo.get(self.combo_tar_evento.get())
        resp = self.usuarios_combo.get(self.combo_tar_resp.get())
        titulo = self.entry_tar_titulo.get().strip()
        if not ev or not resp:
            return messagebox.showwarning("Campos incompletos", "Selecciona evento y responsable.")
        if not titulo:
            return messagebox.showwarning("Campo requerido", "Indica el título de la tarea.")
        flimite = f"{self.obtener_fecha(self.tar_fecha)} {self.entry_tar_hora.get().strip()}"
        try:
            self.ejecutar_consulta(
                "UPDATE tareas SET id_evento=%s, id_responsable=%s, titulo=%s, descripcion=%s, prioridad=%s, estado=%s, fecha_limite=%s "
                "WHERE id_tarea=%s",
                (ev, resp, titulo, self.entry_tar_desc.get(), self.combo_tar_prio.get(), self.combo_tar_estado.get(), flimite, tid)
            )
            self.cargar_datos_tareas()
            messagebox.showinfo("Éxito", "Tarea actualizada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_tarea(self):
        tid = self.tarea_seleccionada_id()
        if tid is None:
            return messagebox.showwarning("Selección requerida", "Selecciona una tarea.")
        if not messagebox.askyesno("Confirmar", "¿Eliminar la tarea seleccionada?"):
            return
        try:
            self.ejecutar_consulta("DELETE FROM tareas WHERE id_tarea=%s", (tid,))
            self.limpiar_form_tarea()
            self.cargar_datos_tareas()
            messagebox.showinfo("Eliminado", "Tarea eliminada.")
        except Exception as e:
            messagebox.showerror("No se pudo eliminar", str(e))

    def cargar_datos_tareas(self):
        try:
            for item in self.tree_tareas.get_children():
                self.tree_tareas.delete(item)
            rows = self.ejecutar_consulta("""
                SELECT tareas.id_tarea, eventos.titulo, usuarios.nombre, tareas.titulo, tareas.estado, tareas.fecha_limite
                FROM tareas
                JOIN eventos ON tareas.id_evento = eventos.id_evento
                JOIN usuarios ON tareas.id_responsable = usuarios.id_usuario
                ORDER BY tareas.fecha_limite
            """, fetch=True)
            for r in rows:
                self.tree_tareas.insert("", "end", values=r)

            for item in self.tree_vencidas.get_children():
                self.tree_vencidas.delete(item)
            vrows = self.ejecutar_consulta(
                "SELECT id_tarea, titulo_evento, responsable, descripcion, estado, fecha_limite FROM vista_tareas_vencidas",
                fetch=True
            )
            for r in vrows:
                self.tree_vencidas.insert("", "end", values=r)

            if hasattr(self, 'combo_tar_resp'):
                self.combo_tar_resp.configure(values=["Seleccione responsable"] + list(self.usuarios_combo.keys()))
                self.combo_tar_evento.configure(values=["Seleccione evento"] + list(self.eventos_combo.keys()))
        except Exception as e:
            print(f"Error cargando tareas: {e}")

    # -------------------- REFRESCO GENERAL --------------------

    def actualizar_todas_las_tablas(self):
        self.cargar_datos_usuarios()
        self.cargar_datos_categorias()
        self.cargar_datos_eventos()
        self.cargar_datos_ubicaciones()
        self.cargar_datos_disponibilidad()
        self.cargar_datos_tareas()


if __name__ == "__main__":
    app = AppAgenda()
    app.mainloop()
