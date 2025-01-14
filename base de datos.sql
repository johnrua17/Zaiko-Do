CREATE TABLE `usuario` (
  `idusuario` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `correo` varchar(50) NOT NULL,
  `contraseña` varchar(200) NOT NULL,
  `role` varchar(50) NOT NULL DEFAULT 'usuario',
  `idplan` int NOT NULL DEFAULT '1',
  `fecha_creacion_plan` date DEFAULT NULL,
  `fecha_expiracion_plan` date DEFAULT NULL,
  `intentos_fallidos` int DEFAULT '0',
  `bloqueado_hasta` datetime DEFAULT NULL,
  `ultimo_intento` datetime DEFAULT NULL,
  PRIMARY KEY (`idusuario`),
  UNIQUE KEY `correo_UNIQUE` (`correo`)
) ENGINE=InnoDB AUTO_INCREMENT=120 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci

CREATE TABLE `ventas` (
  `idventas` int NOT NULL AUTO_INCREMENT,
  `idusuario` int NOT NULL,
  `totalventa` decimal(10,2) NOT NULL,
  `pagocon` decimal(10,2) NOT NULL DEFAULT '0.00',
  `fecha` date NOT NULL,
  `hora` time NOT NULL,
  `metodo_pago` varchar(45) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NOT NULL,
  `idventausuario` int NOT NULL,
  `devuelto` tinyint(1) DEFAULT '0',
  `cliente` varchar(255) DEFAULT NULL,
  `idcliente` bigint DEFAULT NULL,
  `credito` tinyint(1) DEFAULT '0',
  `fecha_servidor` date DEFAULT NULL,
  PRIMARY KEY (`idventas`),
  KEY `idusuario_idx` (`idusuario`) /*!80000 INVISIBLE */,
  CONSTRAINT `idusuario` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=1662 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci

CREATE TABLE `tienda` (
  `idTienda` int NOT NULL AUTO_INCREMENT,
  `idusuario` int DEFAULT NULL,
  `nombre` varchar(45) DEFAULT NULL,
  `direccion` varchar(45) DEFAULT NULL,
  `ciudad` varchar(45) DEFAULT NULL,
  `telefono` varchar(60) DEFAULT NULL,
  `email` varchar(45) DEFAULT NULL,
  `sitio_web` varchar(45) DEFAULT NULL,
  `horario` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`idTienda`),
  KEY `idusuario_idx` (`idusuario`) /*!80000 INVISIBLE */,
  CONSTRAINT `id_usuarios` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb3

CREATE TABLE `suscripciones` (
  `idsuscripcion` int NOT NULL AUTO_INCREMENT,
  `idusuario` int NOT NULL,
  `correo` varchar(255) NOT NULL,
  `idplan` int NOT NULL,
  `token` varchar(255) NOT NULL,
  `estado` enum('pendiente','aprobado','rechazado','anulado') NOT NULL,
  `fecha_creacion` timestamp NOT NULL,
  `fecha_expiracion` datetime DEFAULT NULL,
  PRIMARY KEY (`idsuscripcion`),
  KEY `idusuario` (`idusuario`),
  KEY `idplan` (`idplan`),
  CONSTRAINT `suscripciones_ibfk_1` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`),
  CONSTRAINT `suscripciones_ibfk_2` FOREIGN KEY (`idplan`) REFERENCES `planes` (`idplan`)
) ENGINE=InnoDB AUTO_INCREMENT=96 DEFAULT CHARSET=utf8mb3

CREATE TABLE `registro_abonos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idcredito` int NOT NULL,
  `idusuario` int NOT NULL,
  `monto_abono` decimal(10,2) NOT NULL,
  `fecha_abono` date NOT NULL,
  `hora_abono` time NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idcredito` (`idcredito`),
  KEY `idusuario` (`idusuario`),
  CONSTRAINT `registro_abonos_ibfk_1` FOREIGN KEY (`idcredito`) REFERENCES `creditos` (`idcredito`),
  CONSTRAINT `registro_abonos_ibfk_2` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb3

CREATE TABLE `recuperar_contra` (
  `idrecuperar_contra` int NOT NULL AUTO_INCREMENT,
  `correo` varchar(100) NOT NULL,
  `token` varchar(300) NOT NULL,
  `creado` datetime NOT NULL,
  `expira` datetime NOT NULL,
  `usado` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`idrecuperar_contra`)
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8mb3

CREATE TABLE `productos` (
  `idproductos` int NOT NULL AUTO_INCREMENT,
  `id_usuario` int NOT NULL,
  `Codigo_de_barras` varchar(100) NOT NULL,
  `Nombre` varchar(60) NOT NULL,
  `Descripcion` varchar(70) NOT NULL,
  `Precio_Valor` decimal(12,2) NOT NULL,
  `Precio_Costo` decimal(12,2) NOT NULL,
  `Cantidad` int NOT NULL,
  `Categoria` varchar(70) NOT NULL,
  PRIMARY KEY (`idproductos`),
  KEY `idusuario_idx` (`id_usuario`),
  CONSTRAINT `id_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=947 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci

CREATE TABLE `planes` (
  `idplan` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `precio` float NOT NULL,
  `duracion` varchar(10) NOT NULL,
  `limite_productos` int NOT NULL,
  `limite_ventas` int NOT NULL,
  PRIMARY KEY (`idplan`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci

CREATE TABLE `historial_planes_usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idusuario` int NOT NULL,
  `nombre_plan` varchar(100) NOT NULL,
  `precio` int NOT NULL,
  `duracion` int NOT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idusuario` (`idusuario`),
  CONSTRAINT `historial_planes_usuarios_ibfk_1` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb3

CREATE TABLE `historial_planes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idusuario` int NOT NULL,
  `idplan_anterior` int DEFAULT NULL,
  `fecha_creacion_plan_anterior` date DEFAULT NULL,
  `fecha_expiracion_plan_anterior` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idusuario` (`idusuario`),
  CONSTRAINT `historial_planes_ibfk_1` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb3

CREATE TABLE `detalleventas` (
  `iddetalle` int NOT NULL AUTO_INCREMENT,
  `idventa` int NOT NULL,
  `codigo_de_barras` varchar(45) NOT NULL,
  `nombre` varchar(45) NOT NULL,
  `descripcion` varchar(45) NOT NULL,
  `valor` varchar(45) NOT NULL,
  `costo` varchar(45) NOT NULL,
  `cantidad` varchar(45) NOT NULL,
  `categoria` varchar(45) DEFAULT NULL,
  `idusuario` int DEFAULT NULL,
  `fecha` date DEFAULT NULL,
  PRIMARY KEY (`iddetalle`),
  KEY `idusuario_idx` (`idusuario`) /*!80000 INVISIBLE */
) ENGINE=InnoDB AUTO_INCREMENT=2958 DEFAULT CHARSET=utf8mb3

CREATE TABLE `creditos` (
  `idcredito` int NOT NULL AUTO_INCREMENT,
  `nombre_cliente` varchar(255) NOT NULL,
  `identificacion_cliente` varchar(100) NOT NULL,
  `contacto_cliente` varchar(255) DEFAULT NULL,
  `total_compra` decimal(10,2) DEFAULT NULL,
  `abono` decimal(10,2) DEFAULT NULL,
  `idventausuario` int DEFAULT NULL,
  `idusuario` int DEFAULT NULL,
  `fecha_registro` date DEFAULT NULL,
  `hora` time DEFAULT NULL,
  `nota` varchar(255) DEFAULT NULL,
  `estado` enum('Activo','Pagado') DEFAULT 'Activo',
  PRIMARY KEY (`idcredito`),
  KEY `idusuario` (`idusuario`),
  CONSTRAINT `creditos_ibfk_1` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=106 DEFAULT CHARSET=utf8mb3

CREATE TABLE `clientes` (
  `idcliente` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) NOT NULL,
  `identificacion` varchar(100) NOT NULL,
  `contacto` varchar(255) DEFAULT NULL,
  `fecha_registro` date DEFAULT NULL,
  `idusuario` int DEFAULT NULL,
  PRIMARY KEY (`idcliente`),
  UNIQUE KEY `identificacion` (`identificacion`),
  KEY `fk_usuario` (`idusuario`),
  CONSTRAINT `fk_usuario` FOREIGN KEY (`idusuario`) REFERENCES `usuario` (`idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb3