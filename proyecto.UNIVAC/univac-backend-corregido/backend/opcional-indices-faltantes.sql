-- ============================================================
-- ÍNDICES DE OPTIMIZACIÓN PARA TABLAS DE VENTAS / COMPRAS
-- ------------------------------------------------------------
-- Archivo auxiliar: SOLO crea índices (estructura). No modifica
-- datos, consultas ni resultados.
--
-- Nota sobre nombres reales:
--   * La tabla "ventas" del ejemplo corresponde a comprobantes_ventas
--   * La tabla "compras" corresponde a comprobantes_compras
--   * El detalle/insumos vive en comprobantes_cuerpo
--   * "id_cliente" de comprobantes_cuerpo se llama id_clipro
--
-- Idempotente: si el servidor no soporta "CREATE INDEX IF NOT
-- EXISTS" (MySQL 8), se usa un procedimiento que crea el índice
-- SOLO si no existe el nombre y/o el mismo conjunto de columnas.
-- ============================================================

USE `UnivacERPDb`;

DROP PROCEDURE IF EXISTS crear_indice_optimizacion;
DELIMITER $$
CREATE PROCEDURE crear_indice_optimizacion(IN p_tabla VARCHAR(64), IN p_indice VARCHAR(64), IN p_columnas VARCHAR(255))
BEGIN
    DECLARE v_existe INT DEFAULT 0;

    SELECT COUNT(*) INTO v_existe
      FROM information_schema.statistics
     WHERE table_schema = DATABASE()
       AND table_name   = p_tabla
       AND index_name   = p_indice;

    IF v_existe = 0 THEN
        SELECT COUNT(*) INTO v_existe
          FROM (
            SELECT GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols
              FROM information_schema.statistics
             WHERE table_schema = DATABASE()
               AND table_name   = p_tabla
             GROUP BY index_name
          ) x
         WHERE x.cols = REPLACE(REPLACE(p_columnas, ' ', ''), '`', '');

        IF v_existe = 0 THEN
            SET @sql = CONCAT('CREATE INDEX `', p_indice, '` ON `', p_tabla, '` (', p_columnas, ')');
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
        END IF;
    END IF;
END$$
DELIMITER ;

-- -------------------------------
-- Compras por fecha (faltante):
-- cubre Compras Acumuladas/Provincias/Proveedores y Gastos
-- (el rango por fecha se filtra siempre con id_empresa)
-- -------------------------------
CALL crear_indice_optimizacion('comprobantes_compras', 'idx_opt_compras_emp_fecha', 'id_empresa, fecha');

-- -------------------------------
-- Detalle de ventas por cliente (faltante):
-- id_clipro = id_cliente en comprobantes_cuerpo.
-- Acelera Ventas por Cliente y Ventas por Insumos desagregadas.
-- -------------------------------
CALL crear_indice_optimizacion('comprobantes_cuerpo', 'idx_opt_cuerpo_emp_clipro', 'id_empresa, id_clipro');

-- -------------------------------
-- Ventas por registración (faltante):
-- acelera los reportes mrad=4 (por registracion) de Totales y
-- Acumuladas de Ventas.
-- -------------------------------
CALL crear_indice_optimizacion('comprobantes_ventas', 'idx_opt_ventas_emp_registracion', 'id_empresa, registracion');

-- -------------------------------
-- Ya cubiertos con índices originales (se omiten, no duplican):
--   * ventas fecha:  idx_comprobantesventas_id_fecha (id_empresa, fecha)
--   * ventas periodo: index4 (id_empresa, mes_imputacion, ano_imputacion)
--   * ventas cliente: index8 (id_empresa, id_cliente, fecha)
--   * compras fecha ven.: idx_empresa_proveedor_fecha (id_empresa, id_proveedor, fecha)
--   * compras periodo: idx_comprobantescompras_id_ano_mes (id_empresa, ano_imputacion, mes_imputacion)
--   * cuerpo fecha: index3 (id_empresa, fecha_movimiento)
--   * cuerpo insumo: index4/index5 (id_empresa, id_articulo[, fecha_movimiento])
-- -------------------------------

DROP PROCEDURE IF EXISTS crear_indice_optimizacion;