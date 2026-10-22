-- ============================================================
-- ÍNDICES DE RENDIMIENTO PARA REPORTES (ERP)
-- ------------------------------------------------------------
-- ACELERA la carga de TODOS los reportes SIN modificar ninguna
-- consulta SQL ni NINGÚN dato.
--
-- Solo agrega índices (estructura/optimización). Los resultados
-- de las consultas son idénticos, solo se busca más rápido.
--
-- Es SEGURO e IDEMPOTENTE: cada índice se crea SOLO si no existe.
-- No borra ni modifica datos.
-- ============================================================

USE `UnivacERPDb`;

-- -------------------------------
-- Procedimiento auxiliar (seguro)
-- -------------------------------
DROP PROCEDURE IF EXISTS crear_indice_si_no_existe;
DELIMITER $$
CREATE PROCEDURE crear_indice_si_no_existe(IN p_tabla VARCHAR(64), IN p_indice VARCHAR(64), IN p_columnas VARCHAR(255))
BEGIN
    DECLARE v_cont INT DEFAULT 0;
    SELECT COUNT(*)
      INTO v_cont
      FROM information_schema.statistics
     WHERE table_schema = DATABASE()
       AND table_name   = p_tabla
       AND index_name   = p_indice;
    IF v_cont = 0 THEN
        SET @sql = CONCAT('CREATE INDEX `', p_indice, '` ON `', p_tabla, '` (', p_columnas, ')');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- -------------------------------
-- comprobantes_cuerpo  (la tabla MÁS pesada)
-- Compras/Ventas por Insumos, Ventas por Productos,
-- Movimientos de Insumos/Productos/Artículos
-- -------------------------------
CALL crear_indice_si_no_existe('comprobantes_cuerpo', 'idx_cuerpo_emp_fecha',   'id_empresa, fecha_movimiento');
CALL crear_indice_si_no_existe('comprobantes_cuerpo', 'idx_cuerpo_emp_ident',   'id_empresa, identificacion');
CALL crear_indice_si_no_existe('comprobantes_cuerpo', 'idx_cuerpo_emp_reg',     'id_empresa, registracion');

-- -------------------------------
-- comprobantes_compras
-- Compras Acumuladas, Provincias, Proveedores, Gastos, Dashboard
-- -------------------------------
CALL crear_indice_si_no_existe('comprobantes_compras', 'idx_compras_emp_fecha',  'id_empresa, fecha');
CALL crear_indice_si_no_existe('comprobantes_compras', 'idx_compras_emp_imput',  'id_empresa, ano_imputacion, mes_imputacion');
CALL crear_indice_si_no_existe('comprobantes_compras', 'idx_compras_emp_reg',    'id_empresa, registracion');
CALL crear_indice_si_no_existe('comprobantes_compras', 'idx_compras_emp_prov',   'id_empresa, id_proveedor');
CALL crear_indice_si_no_existe('comprobantes_compras', 'idx_compras_emp_provin', 'id_empresa, id_provincia');

-- -------------------------------
-- comprobantes_ventas
-- Ventas Acumuladas, Dashboard
-- -------------------------------
CALL crear_indice_si_no_existe('comprobantes_ventas', 'idx_ventas_emp_fecha', 'id_empresa, fecha');
CALL crear_indice_si_no_existe('comprobantes_ventas', 'idx_ventas_emp_imput', 'id_empresa, ano_imputacion, mes_imputacion');
CALL crear_indice_si_no_existe('comprobantes_ventas', 'idx_ventas_emp_forma', 'id_empresa, forma');

-- -------------------------------
-- cheques (Dashboard: cartera, vence, recibidos, entregados)
-- -------------------------------
CALL crear_indice_si_no_existe('cheques', 'idx_cheques_emp_estado', 'id_empresa, id_endosante, id_esporadico, devuelto');
CALL crear_indice_si_no_existe('cheques', 'idx_cheques_emp_vto',    'id_empresa, fecha_vencimiento');
CALL crear_indice_si_no_existe('cheques', 'idx_cheques_emp_ing',    'id_empresa, fecha_ingreso');
CALL crear_indice_si_no_existe('cheques', 'idx_cheques_emp_ent',    'id_empresa, fecha_entrega');

-- -------------------------------
-- cuentas_corrientes_clientes / proveedores (Dashboard)
-- -------------------------------
CALL crear_indice_si_no_existe('cuentas_corrientes_clientes',    'idx_cc_clientes_emp_vto', 'id_empresa, fecha_vencimiento');
CALL crear_indice_si_no_existe('cuentas_corrientes_proveedores', 'idx_cc_prov_emp_vto',     'id_empresa, fecha_vencimiento');

-- -------------------------------
-- bancos (Dashboard)
-- -------------------------------
CALL crear_indice_si_no_existe('bancos', 'idx_bancos_emp_ref_vto', 'id_empresa, id_referencia, fecha_vencimiento');

-- -------------------------------
-- ingresos_egresos (Dashboard)
-- -------------------------------
CALL crear_indice_si_no_existe('ingresos_egresos', 'idx_ingegr_emp_fecha', 'id_empresa, fecha');
CALL crear_indice_si_no_existe('ingresos_egresos', 'idx_ingegr_emp_tipo',  'id_empresa, id_tipo_movimiento');

-- -------------------------------
-- articulos (consultas por JOIN)
-- -------------------------------
CALL crear_indice_si_no_existe('articulos', 'idx_articulos_emp', 'id_empresa, id');

-- -------------------------------
-- Limpieza (opcional) tras la primera ejecución
-- -------------------------------
DROP PROCEDURE IF EXISTS crear_indice_si_no_existe;
