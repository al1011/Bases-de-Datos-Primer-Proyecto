-- Crear la base de datos
--CREATE DATABASE agenda;
CREATE SCHEMA prototipo;

-- Configurar el search_path para que las tablas se creen dentro de ese esquema
-- y se busquen ahí automáticamente
SET search_path TO prototipo, public;

-- 1. Usuarios
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    fecha_registro DATE DEFAULT CURRENT_DATE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

-- 2. Contactos (RF02, RE02, RN02)
CREATE TABLE usuario_telefonos (
    id_usuario INT REFERENCES usuarios(id_usuario),
    telefono VARCHAR(20),
    PRIMARY KEY (id_usuario, telefono)
);

CREATE TABLE usuario_emails (
    id_usuario INT REFERENCES usuarios(id_usuario),
    email VARCHAR(100),
    PRIMARY KEY (id_usuario, email)
);

-- 3. Categorías (RF03, RE05, RN04)
CREATE TABLE categorias (
    id_categoria SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    id_categoria_padre INT REFERENCES categorias(id_categoria)
    -- NOTA: La raíz tendría id_categoria_padre NULL
);

-- 4. Eventos (RF04, RE04)
CREATE TABLE eventos (
    id_evento SERIAL PRIMARY KEY,
    id_usuario_propietario INT NOT NULL REFERENCES usuarios(id_usuario),
    id_categoria INT NOT NULL REFERENCES categorias(id_categoria),
    titulo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_fin TIMESTAMP NOT NULL,
    CONSTRAINT check_fechas CHECK (fecha_fin > fecha_inicio)
);

-- 5. Participación (RF05, RE01, RN01, RN05)
CREATE TABLE participaciones (
    id_evento INT REFERENCES eventos(id_evento) ON DELETE CASCADE,
    id_invitado INT REFERENCES usuarios(id_usuario),
    rol VARCHAR(50),
    estado_confirmacion VARCHAR(20) DEFAULT 'pendiente',
    PRIMARY KEY (id_evento, id_invitado)
);

-- 6. Log de Accesos (RF06)
CREATE TABLE log_accesos (
    id_log SERIAL PRIMARY KEY,
    id_usuario INT REFERENCES usuarios(id_usuario),
    fecha_acceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Implementación de Cálculos Dinámicos (RF07, RE03, RN03) mediante vistas

-- Vista para Antigüedad
CREATE VIEW vista_antiguedad_usuarios AS
SELECT 
    id_usuario, 
    nombre, 
    fecha_registro,
    age(CURRENT_DATE, fecha_registro) AS antiguedad
FROM usuarios;

-- Vista para Duración de eventos diarios
CREATE VIEW vista_duracion_eventos_diarios AS
SELECT 
    id_usuario_propietario,
    fecha_inicio::DATE AS dia,
    SUM(EXTRACT(EPOCH FROM (fecha_fin - fecha_inicio))/60) AS duracion_total_minutos
FROM eventos
GROUP BY id_usuario_propietario, fecha_inicio::DATE;

--Integridad y Prevención de Ciclos (RE05)
--Para evitar ciclos en la jerarquía de categorías, podemos usar una función 
--que verifique el ancestro antes de insertar o actualizar:

CREATE OR REPLACE FUNCTION evitar_ciclo_categorias()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.id_categoria_padre = NEW.id_categoria THEN
        RAISE EXCEPTION 'Una categoría no puede ser padre de sí misma.';
    END IF;
    -- Aquí se podría añadir una consulta recursiva para validar ancestros, 
    -- pero para Postgres 14 es altamente eficiente usar el camino (path) o este chequeo simple.
      RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_evitar_ciclo
BEFORE INSERT OR UPDATE ON categorias
FOR EACH ROW EXECUTE FUNCTION evitar_ciclo_categorias();

	--Módulo de Gestión de Ubicaciones (RF-08 a RF-10)
-- 1. Tabla de Ubicaciones
CREATE TABLE ubicaciones (
    id_ubicacion SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(200),
    ciudad VARCHAR(100) NOT NULL,
    capacidad INT CHECK (capacidad > 0)
);

-- 2. Modifica la tabla eventos existente para agregar la FK
ALTER TABLE eventos
ADD COLUMN id_ubicacion INT REFERENCES ubicaciones(id_ubicacion) ON DELETE SET NULL;

-- 3. Crear la funcion y el trigger
CREATE OR REPLACE FUNCTION verificar_traslape_ubicacion()
RETURNS TRIGGER AS $$
BEGIN
    -- Se verifica si ya existe un evento en la misma ubicacion que choque en las fechas/horas
    IF EXISTS (
        SELECT 1
        FROM eventos
        WHERE eventos.id_ubicacion = NEW.id_ubicacion
          -- Se ignora el mismo evento en caso de que sea una actualizacion
          AND eventos.id_evento != COALESCE(NEW.id_evento, -1) 
          AND eventos.fecha_inicio < NEW.fecha_fin
          AND eventos.fecha_fin > NEW.fecha_inicio
    ) THEN
        RAISE EXCEPTION 'Traslape espacial: La ubicación ya está ocupada en ese horario.';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevenir_traslapes
BEFORE INSERT OR UPDATE ON eventos
FOR EACH ROW
EXECUTE FUNCTION verificar_traslape_ubicacion();
	
-- 4. Vista para analisis de ocupacion
CREATE VIEW vista_ocupacion_ubicaciones AS
SELECT 
    ubicaciones.id_ubicacion,
    ubicaciones.nombre,
    ubicaciones.capacidad,
    COUNT(eventos.id_evento) AS total_eventos_programados
FROM ubicaciones
LEFT JOIN eventos ON ubicaciones.id_ubicacion = eventos.id_ubicacion
GROUP BY 
    ubicaciones.id_ubicacion,
    ubicaciones.nombre,
    ubicaciones.capacidad;
	
--Módulo de Disponibilidad de Usuarios y Gestión de Tiempos (RF-11 y RF-12)
-- 1. Tabla de Disponibilidad de Usuarios
CREATE TABLE disponibilidad_usuarios (
    id_disponibilidad SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    estado VARCHAR(20) NOT NULL,
    
    CONSTRAINT check_estado_disponibilidad CHECK (estado IN ('disponible', 'ocupado', 'no disponible')),
    CONSTRAINT check_horario_valido CHECK (hora_inicio < hora_fin)
);

-- 2. Funcion y trigger para evitar concurrencia en los intervalos del usuario
CREATE OR REPLACE FUNCTION verificar_concurrencia_disponibilidad()
RETURNS TRIGGER AS $$
BEGIN
    -- Busca si el usuario ya tiene un bloque ese mismo dia con choque de horarios
    IF EXISTS (
        SELECT 1
        FROM disponibilidad_usuarios
        WHERE disponibilidad_usuarios.id_usuario = NEW.id_usuario
          AND disponibilidad_usuarios.fecha = NEW.fecha
          AND disponibilidad_usuarios.id_disponibilidad != COALESCE(NEW.id_disponibilidad, -1)
          AND disponibilidad_usuarios.hora_inicio < NEW.hora_fin
          AND disponibilidad_usuarios.hora_fin > NEW.hora_inicio
    ) THEN
        RAISE EXCEPTION 'Concurrencia detectada: El usuario ya tiene un registro que choca en este intervalo horario.';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevenir_concurrencia_usuarios
BEFORE INSERT OR UPDATE ON disponibilidad_usuarios
FOR EACH ROW
EXECUTE FUNCTION verificar_concurrencia_disponibilidad();

-- 3. Vista para resolver consultas de intervalos horarios
CREATE VIEW vista_intervalos_disponibilidad AS
SELECT 
    usuarios.id_usuario,
    usuarios.nombre || ' ' || usuarios.apellido AS nombre_completo,
    disponibilidad_usuarios.fecha,
    disponibilidad_usuarios.hora_inicio,
    disponibilidad_usuarios.hora_fin,
    disponibilidad_usuarios.estado
FROM usuarios
JOIN disponibilidad_usuarios ON usuarios.id_usuario = disponibilidad_usuarios.id_usuario;

--Módulo de Tareas Asociadas a Eventos (RF-15 a RF-17)
-- 1. Crear la tabla
CREATE TABLE tareas (
    id_tarea SERIAL PRIMARY KEY,
    id_evento INT NOT NULL REFERENCES eventos(id_evento) ON DELETE CASCADE,
    id_responsable INT NOT NULL REFERENCES usuarios(id_usuario),
    titulo VARCHAR(100) NOT NULL,
    descripcion VARCHAR(150) NOT NULL,
    prioridad VARCHAR(20) DEFAULT 'Media',
    estado VARCHAR(20) DEFAULT 'Pendiente',
    fecha_limite TIMESTAMP NOT NULL,
	
    -- Restricciones para que no se ingresen datos invalidos
    CONSTRAINT check_prioridad CHECK (prioridad IN ('Alta', 'Media', 'Baja')),
    CONSTRAINT check_estado CHECK (estado IN ('Pendiente', 'En progreso', 'Completada', 'Cancelada'))
);

-- 2. Vista para el reporte de plazos vencidos
CREATE VIEW vista_tareas_vencidas AS
SELECT 
    tareas.id_tarea,
    eventos.titulo AS titulo_evento,
    usuarios.nombre || ' ' || usuarios.apellido AS responsable,
    tareas.descripcion,
    tareas.prioridad,
    tareas.estado,
    tareas.fecha_limite
FROM tareas 
JOIN eventos ON tareas.id_evento = eventos.id_evento
JOIN usuarios ON tareas.id_responsable = usuarios.id_usuario
-- Filtro para tareas que no estan listas y que la fecha ya paso
WHERE tareas.estado NOT IN ('Completada', 'Cancelada')
  AND tareas.fecha_limite < CURRENT_TIMESTAMP;

