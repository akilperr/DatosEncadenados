// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.7.0 <0.9.0;

/**
 * @title MiInversion
 * @dev Sistema que permite:
 *  - Crear acciones (solo owner)
 *  - Suscribirse a niveles (Basico, Intermedio, Avanzado)
 *  - Convertirse en profesor y cobrar por clases
 *  - Comprar y vender acciones con simulación de mercado
 */
contract MiInversion {

    // ------------------------------------------------------------
    //            ENUM — ESTRUCTURAS — VARIABLES PRINCIPALES
    // ------------------------------------------------------------

    /**
     * @dev Niveles de suscripción disponibles.
     * - Nulo: sin suscripción.
     * - Basico/Intermedio/Avanzado: afectan a comisiones al comprar acciones.
     */
    enum nivelSuscripcion {
        Nulo,
        Basico,
        Intermedio,
        Avanzado
    }

    /**
     * @dev Información almacenada de cada usuario.
     * - subscription_time: momento en el que se suscribió.
     * - es_profe: indica si es profesor.
     * - precio_clase: precio que cobra por clase.
     * - nivel: nivel de suscripción actual.
     * - acciones_compradas: mapping de acciones propiedad del usuario.
     */
    struct Usuario {
        uint256 subscription_time;
        bool es_profe;
        uint256 precio_clase;
        nivelSuscripcion nivel;
        mapping(string => Accion_Us) acciones_compradas;
    }

    // Lista de todos los usuarios registrados (dentro del mapping)
    mapping(address => Usuario) public Usuarios;

    /**
     * @dev Acción disponible en el sistema.
     * - nombre: nombre identificador.
     * - precio_actual: precio en wei (o unidad elegida por el owner).
     */
    struct Accion {
        string nombre;
        uint256 precio_actual;
    }

    // Lista de acciones indexadas por nombre
    mapping(string => Accion) public Acciones;

    /**
     * @dev Información de las acciones que un usuario tiene.
     * - accion: nombre de la acción.
     * - CompraAccion_time: momento de compra.
     * - Cantidad_acciones: número de unidades compradas.
     * - Cantidad_gastada: total gastado.
     */
    struct Accion_Us {
        string accion;
        uint256 CompraAccion_time;
        uint256 Cantidad_acciones;
        uint256 Cantidad_gastada;
    }

    // Dirección del dueño del contrato (administrador general)
    address payable public owner;

    /**
     * @dev Constructor: guarda msg.sender como dueño.
     */
    constructor() {
        owner = payable(msg.sender);
        
        // Acciones predeterminadas del sistema
        Acciones["AMD"] = Accion("AMD", 12 ether);
        Acciones["NIO"] = Accion("NIO", 5 ether);
        Acciones["BTC"] = Accion("BTC", 20 ether);

    }

    // ------------------------------------------------------------
    //                         EVENTOS
    // ------------------------------------------------------------

    // Se emiten para monitorear toda la actividad del sistema
    event AccionCreadaOActualizada(string nombre, uint256 precio);
    event SuscripcionHecha(address usuario, nivelSuscripcion nivel, uint256 precio);
    event SuscripcionCancelada(address usuario);
    event ProfesorActivado(address usuario, uint256 precio_clase);
    event ProfesorDesactivado(address usuario);
    event ClasePagada(address alumno, address profesor, uint256 precio);
    event AccionComprada(address usuario, string accion, uint256 cantidad, uint256 gastado);
    event AccionVendida(address usuario, string accion, uint256 cantidad, uint256 recibido);

    // ------------------------------------------------------------
    //                        OWNER ONLY
    // ------------------------------------------------------------

    /**
     * @dev Permite al owner crear o actualizar el precio de una acción.
     * Requiere:
     *  - que el caller sea owner
     *  - que el nombre no esté vacío
     *  - que el precio sea mayor que 0
     */
    function addAcciones(string calldata nombre, uint256 precio_actual) public {
        require(msg.sender == owner, "Solo owner");
        require(bytes(nombre).length > 0, "Nombre vacio");
        require(precio_actual > 0, "Precio debe ser > 0");

        // Registrar acción en el mapping
        Acciones[nombre].nombre = nombre;
        Acciones[nombre].precio_actual = precio_actual * 1 ether;

        emit AccionCreadaOActualizada(nombre, precio_actual);
    }


    function borrarAcciones(string calldata nombre) public {
        require(msg.sender == owner, "Solo owner");
        require(bytes(nombre).length > 0, "Nombre vacio");
        require(Acciones[nombre].precio_actual > 0, "Accion no existe");
        // Registrar acción en el mapping
        Acciones[nombre].nombre = "";
        Acciones[nombre].precio_actual =0;
        emit AccionCreadaOActualizada(nombre, 0);
    }

    /**
     * @dev Permite al owner revisar si a un usuario se le debe caducar la suscripción.
     * Si han pasado +30 días desde su suscripción, se le baja a nivel Nulo.
     */
    function revisar_suscripcion(address user) external returns (nivelSuscripcion) {
        require(msg.sender == owner, "Solo owner");

        Usuario storage u = Usuarios[user];

        // Si no está en Nulo y se le ha pasado el tiempo → resetear
        if (
            u.nivel != nivelSuscripcion.Nulo &&
            (block.timestamp - u.subscription_time) >= (30 days)
        ) {
            u.nivel = nivelSuscripcion.Nulo;
        }

        return u.nivel;
    }

    // ------------------------------------------------------------
    //                      SUSCRIPCIONES
    // ------------------------------------------------------------

    /**
     * @dev El usuario paga para suscribirse a un nivel.
     * Los niveles tienen precios fijos:
     * - Basico → 2 ETH
     * - Intermedio → 6 ETH
     * - Avanzado → 10 ETH
     *
     * El contrato envía este dinero al owner.
     */
    function suscribirse(nivelSuscripcion nivel) external payable {
        Usuario storage u = Usuarios[msg.sender];

        require(u.nivel == nivelSuscripcion.Nulo, "Ya estas suscrito");
        require(nivel != nivelSuscripcion.Nulo, "Nivel invalido");

        uint256 precio;
        if (nivel == nivelSuscripcion.Basico) precio = 2 ether;
        if (nivel == nivelSuscripcion.Intermedio) precio = 6 ether;
        if (nivel == nivelSuscripcion.Avanzado) precio = 10 ether;

        require(msg.value >= precio, "Dinero insuficiente, Basico 2ETH, Intermedio 6 ETH, avanzado 10 ETH");

        // Si paga de más, se le devuelve el sobrante
        uint256 sobrante = msg.value - precio;
        if (sobrante > 0) {
            require(payable(msg.sender).send(sobrante), "Fallo devolver sobras");
        }

        // Pago al owner
        require(owner.send(precio), "Fallo al pagar subscripcion");

        // Guardar datos de suscripción
        u.subscription_time = block.timestamp;
        u.nivel = nivel;

        emit SuscripcionHecha(msg.sender, nivel, precio);
    }

    /**
     * @dev Cancela la suscripción sin reembolso.
     * El nivel vuelve a Nulo.
     */
    function cancelar_Suscripcion() public {
        Usuario storage u = Usuarios[msg.sender];
        require(u.nivel != nivelSuscripcion.Nulo, "No estas suscrito");

        u.nivel = nivelSuscripcion.Nulo;
        u.subscription_time = 0;

        emit SuscripcionCancelada(msg.sender);
    }

    /**
     * @dev Simple getter que devuelve el nivel actual de suscripción.
     */
    function ver_suscripcion() external view returns (nivelSuscripcion) {
        return Usuarios[msg.sender].nivel;
    }

    // ------------------------------------------------------------
    //                     PROFESOR / CLASES
    // ------------------------------------------------------------

    /**
     * @dev Convierte al usuario en profesor con un precio de clase.
     */
    function ser_profesor(uint256 precio_por_clase) public {
        Usuario storage u = Usuarios[msg.sender];
        require(!u.es_profe, "Ya eres profe");

        u.es_profe = true;
        u.precio_clase = precio_por_clase * 1 ether;

        emit ProfesorActivado(msg.sender, precio_por_clase);
    }

    /**
     * @dev El usuario deja de ser profesor.
     */
    function cancelar_modo_profe() public {
        Usuario storage u = Usuarios[msg.sender];
        require(u.es_profe, "No eres profe");

        u.es_profe = false;
        u.precio_clase = 0;

        emit ProfesorDesactivado(msg.sender);
    }

    /**
     * @dev Un alumno paga al profesor por su clase.
     * Si envía más dinero de la cuenta, se devuelve la diferencia.
     */
    function pedir_clase(address profesor) external payable {
        Usuario storage profe = Usuarios[profesor];

        require(profe.es_profe, "No es profesor");
        require(msg.value >= profe.precio_clase, "Pago insuficiente");

        uint256 sobra = msg.value - profe.precio_clase;

        // Devolver sobrante al alumno
        if (sobra > 0) {
            require(payable(msg.sender).send(sobra), "Fallo devolver sobra");
        }

        // Pago directo al profesor
        require(payable(profesor).send(profe.precio_clase), "Fallo pago a profesor");

        emit ClasePagada(msg.sender, profesor, profe.precio_clase);
    }

    // ------------------------------------------------------------
    //                     COMPRA DE ACCIONES
    // ------------------------------------------------------------

    /**
     * @dev Un usuario compra acciones. El precio depende de la acción.
     * Sólo puede comprar acciones enteras.
     */
    function comprar_acciones(string calldata accion) external payable {
        require(Acciones[accion].precio_actual > 0, "Accion no existe");

        Usuario storage user = Usuarios[msg.sender];
        uint256 precioAccion = Acciones[accion].precio_actual;

        require(msg.value >= precioAccion, "Dinero insuficiente para comprar 1 accion");

        // Todo el dinero disponible es para comprar acciones
        uint256 disponible = msg.value;

        // Cantidad entera posible
        uint256 cantidad = disponible / precioAccion;
        require(cantidad > 0, "No alcanza para 1 accion");

        uint256 gastado = cantidad * precioAccion;
        uint256 sobrante = disponible - gastado;

        // Devolver sobras si existen
        if (sobrante > 0) {
            require(payable(msg.sender).send(sobrante), "Fallo devolver sobras");
        }

        // Registrar compra
        Accion_Us storage reg = user.acciones_compradas[accion];
        reg.accion = accion;
        reg.CompraAccion_time = block.timestamp;
        reg.Cantidad_acciones += cantidad;
        reg.Cantidad_gastada += gastado;
        emit AccionComprada(msg.sender, accion, cantidad, gastado);
    }


    // ------------------------------------------------------------
    //                      VENTA DE ACCIONES
    // ------------------------------------------------------------

    /**
     * @dev Vende acciones con simulación de mercado.
     * - Calcula comisión de salida: 1 ETH por mes desde compra.
     * - Precio simulado: multiplicador pseudo-aleatorio entre 0.1 y 3
     *   con mayor probabilidad en 0.8–1.2.
     * - Si vende todas, reinicia el registro.
     */
    function vender_acciones(string calldata accion, uint256 cantidad) external {
        require(Acciones[accion].precio_actual > 0, "Accion no existe");

        Accion_Us storage reg = Usuarios[msg.sender].acciones_compradas[accion];

        require(reg.Cantidad_acciones > 0, "No tienes esa accion");
        require(cantidad > 0, "Cantidad invalida");
        require(reg.Cantidad_acciones >= cantidad, "No suficiente cantidad");

        // -----------------------------------------------------
        // 1. Determinar COMISION INICIAL según nivel
        // -----------------------------------------------------
        uint256 comisionInicial;

        if (Usuarios[msg.sender].nivel == nivelSuscripcion.Nulo) comisionInicial = 5 ether;
        else if (Usuarios[msg.sender].nivel == nivelSuscripcion.Basico) comisionInicial = 4 ether;
        else if (Usuarios[msg.sender].nivel == nivelSuscripcion.Intermedio) comisionInicial = 3 ether;
        else comisionInicial = 2 ether; // Avanzado

        // -----------------------------------------------------
        // 2. Calcular meses transcurridos desde compra
        // -----------------------------------------------------
        uint256 meses = (block.timestamp - reg.CompraAccion_time) / (30 days);

        // Cada mes reduce la comisión en 0.1 ETH
        // Comisión mínima = 1 ETH
        uint256 comision;

        if ((comisionInicial - (meses * 0.1 ether)) < 1) {
            comision = 1 ether; // no puede bajar de 1
        } else {
            comision = comisionInicial - (meses * 0.1 ether);
        }

        // -----------------------------------------------------
        // 3. Simulación de precio de venta
        // -----------------------------------------------------
        uint256 precioBase = Acciones[accion].precio_actual;

        uint256 rand = uint256(
            keccak256(abi.encodePacked(block.timestamp, msg.sender, precioBase))
        ) % 1000;

        uint256 multiplicador;
        if (rand < 600) multiplicador = 80 + (rand % 40);  // 0.8–1.2
        else multiplicador = 10 + (rand % 290);            // 0.1–3.0

        uint256 bruto = precioBase * multiplicador;
        uint256 precioVenta = bruto / 100;
        if (bruto % 100 != 0) precioVenta++;

        // -----------------------------------------------------
        // 4. Calcular dinero total generado
        // -----------------------------------------------------
        uint256 ganancias = precioVenta * cantidad;

        // -----------------------------------------------------
        // 5. Aplicar comisión (máx puede comerlo todo)
        // -----------------------------------------------------
        uint256 neto = ganancias > comision ? ganancias - comision : 0;

        // -----------------------------------------------------
        // 6. Pagar comisión al owner
        // -----------------------------------------------------
        require(owner.send(comision), "No se pudo pagar comision mantenimiento");

        // -----------------------------------------------------
        // 7. Pagar al usuario su ganancia neta
        // -----------------------------------------------------
        if (neto > 0) {
            require(payable(msg.sender).send(neto), "No se pudo enviar venta");
        }

        // -----------------------------------------------------
        // 8. Actualizar registro del usuario
        // -----------------------------------------------------
        reg.Cantidad_gastada = (cantidad/reg.Cantidad_acciones)*reg.Cantidad_gastada;
        reg.Cantidad_acciones -= cantidad;
        

        if (reg.Cantidad_acciones == 0) {
            reg.accion = "";
            reg.CompraAccion_time = 0;
            reg.Cantidad_gastada = 0;
        }

        emit AccionVendida(msg.sender, accion, cantidad, neto);
    }

    // ------------------------------------------------------------
    //                          VISTAS
    // ------------------------------------------------------------
    /**
     * @dev Devuelve información sobre una acción específica que el usuario posea.
     */
    function ver_mi_accion(string calldata accion) external view returns (
            string memory nombre,
            uint256 fecha,
            uint256 cantidad,
            uint256 gastado
        )
    {
        Accion_Us storage reg = Usuarios[msg.sender].acciones_compradas[accion];

        require(reg.Cantidad_acciones > 0, "No tienes esa accion");

        return (
            reg.accion,
            reg.CompraAccion_time,
            reg.Cantidad_acciones,
            reg.Cantidad_gastada
        );
    }
}
