# WAOS Vertical Portfolio

Portafolio vertical integrado a WAOS para vender la plataforma como sistema operativo conversacional sobre WhatsApp, no como bot horizontal.

## Marco maestro

- WAOS se posiciona como control tower comercial y operativa: inbox inteligente, takeover humano, memoria por lead, follow-ups, agenda, pagos, catálogo, promociones, revenue, operaciones, insights, launch y despliegue.
- Cada vertical baja a buyer, objetos nativos, pipeline, playbook del bot, automatizaciones y KPIs.
- La capa vive en `backend/app/data/vertical_portfolio_updates.json`, se expone por `/api/v1/verticals` y se consulta desde `/verticals` en frontend.

## Verticales incluidas

### WAOS Fitness

- Tier: tier_1
- Tesis: Sistema operativo conversacional para gimnasios, estudios y academias deportivas que convierte captación, prueba, inscripción, asistencia y retención en un flujo operable desde WhatsApp.
- Buyer principal: Dueño de gimnasio o director comercial/operativo
- Problema: Los negocios fitness pierden dinero porque demasiados leads preguntan pero no prueban, demasiadas pruebas no se convierten y demasiados alumnos se enfrían por falta de seguimiento, asistencia y reactivación.
- Promesa: Cada conversación termina en una acción clara: clase muestra, evaluación, inscripción, renovación o retorno.
- Monetiza: inscripción, primer mes, paquetes, membresías, personal training, nutrición, upgrades
- Subverticales: gym tradicional, gimnasio boutique, entrenamiento funcional, cross training, spinning, personal training, boxeo, MMA, jiu-jitsu, taekwondo, pilates, yoga, running club, academias deportivas

### WAOS Dental

- Tier: tier_1
- Tesis: Sistema operativo conversacional para clínicas dentales que mueve al paciente desde urgencia o valoración hasta tratamiento por fases, control y recall.
- Buyer principal: Director de clínica dental o gerente comercial
- Problema: Las clínicas dentales pierden dinero porque no separan urgencia de valoración, no persiguen presupuestos no aceptados, no sostienen tratamientos por fases y no activan recall suficiente.
- Promesa: Cada paciente avanza con un siguiente paso claro: urgencia, valoración, aceptación, siguiente fase o control.
- Monetiza: valoración, anticipo, tratamiento por fases, financiamiento, controles, recalls
- Subverticales: odontología general, ortodoncia, alineadores, implantología, periodoncia, endodoncia, estética dental, odontopediatría, rehabilitación oral, cirugía dental

### WAOS Aesthetic

- Tier: tier_1
- Tesis: Sistema operativo conversacional para medicina estética y wellness premium que convierte leads aspiracionales en valoración, paquete, sesiones, mantenimiento y recompra.
- Buyer principal: Dueño o gerente comercial de clínica estética / med spa
- Problema: Estética pierde valor por mala respuesta inicial, poca confianza, poco seguimiento, baja venta de paquete y casi nada de mantenimiento sistemático.
- Promesa: Cada conversación termina en una siguiente acción clara: valoración, anticipo, sesión, paquete o mantenimiento.
- Monetiza: valoración, sesión individual, paquete, anticipo, planes de mantenimiento, cross-sell
- Subverticales: medicina estética, med spa, depilación láser, faciales avanzados, contouring corporal, skin clinic, anti-aging, rejuvenecimiento, aparatología estética, wellness premium

### WAOS Vet

- Tier: tier_2
- Tesis: Sistema operativo conversacional para veterinarias y pet care que conecta consulta, prevención, grooming, planes y recurrencia alrededor de la mascota.
- Buyer principal: Dueño de clínica veterinaria o pet care
- Problema: Veterinarias y pet care suelen mezclar salud, grooming y prevención en conversaciones separadas, perdiendo historial, recordatorios y servicios recurrentes.
- Promesa: Cada mascota se gestiona como cuenta recurrente con próxima acción clara.
- Monetiza: consulta, vacunas, grooming, hotel/daycare, planes preventivos, nutrición
- Subverticales: clínica veterinaria, hospital veterinario, vacunación, grooming, hotel, daycare, rehabilitación, nutrición veterinaria, planes preventivos

### WAOS Real Estate

- Tier: tier_1
- Tesis: Sistema operativo conversacional para inmobiliaria y lifecycle de propiedades que perfila, recomienda, agenda visitas, sigue y reactiva oportunidades largas.
- Buyer principal: Director comercial o broker principal
- Problema: Inmobiliaria pierde tiempo y cierres por leads mal calificados, mucho trabajo manual del asesor, poco seguimiento post visita y reactivación débil.
- Promesa: Cada conversación termina en visita, propuesta, reubicación de inventario o reactivación futura.
- Monetiza: visita, llamada calificada, cierre de venta, cierre de renta, administración posterior, renovación
- Subverticales: venta residencial, renta residencial, desarrollos, preventa, lujo, brokers hipotecarios, property management, administración de rentas, comercial, inversión inmobiliaria

### WAOS Auto Service

- Tier: tier_2
- Tesis: Sistema operativo conversacional para talleres, servicio automotriz y aftermarket que ordena intake, cotización, aprobación, estatus y mantenimiento futuro.
- Buyer principal: Dueño o gerente de taller/centro de servicio
- Problema: Auto service pierde confianza y dinero por intake desordenado, cotización tardía, falta de visibilidad del avance y ausencia de seguimiento al siguiente mantenimiento.
- Promesa: Cada solicitud se vuelve una orden clara con próximo paso visible.
- Monetiza: revisión, servicio, reparación, aprobación extra, entrega, mantenimiento recurrente
- Subverticales: taller mecánico, centro de servicio, servicio eléctrico, llantera, hojalatería y pintura, detailing, PPF, wraps, lavado premium, accesorios

### WAOS Education

- Tier: tier_1
- Tesis: Sistema operativo conversacional para admisiones, inscripción y renovación que convierte interés académico en entrevista, documentos, pago y continuidad.
- Buyer principal: Director de admisiones o crecimiento
- Problema: Educación pierde conversión por exceso de respuestas manuales, mala persecución documental, seguimiento débil y poca estructura para cerrar inscripciones y renovaciones.
- Promesa: Cada prospecto avanza con siguiente paso visible hasta convertirse en alumno pagado y renovado.
- Monetiza: entrevista/tour, inscripción, colegiatura inicial, renovación, upgrade de programas
- Subverticales: colegios privados, universidades privadas, idiomas, academias, tutorías, bootcamps, after school, formación técnica, educación ejecutiva, educación continua

### WAOS Beauty

- Tier: tier_2
- Tesis: Sistema operativo conversacional para belleza personal y self-care que llena agenda, cobra anticipos, reduce no-show y multiplica rebook.
- Buyer principal: Dueño de salón/beauty lounge o gerente operativo
- Problema: Beauty vive en el caos del inbox: mucha pregunta repetitiva, mucha disponibilidad manual, mucho no-show, poco anticipo y poca recompra estructurada.
- Promesa: Cada conversación debe cerrar en cita, anticipo, add-on o siguiente visita.
- Monetiza: cita, anticipo, add-ons, paquetes, frecuencia ideal, eventos especiales
- Subverticales: salón, barbería, uñas, lashes, brows, maquillaje, peinado social, bridal beauty, hair color, skincare studio

### WAOS Field Services

- Tier: tier_1
- Tesis: Sistema operativo conversacional para servicios en sitio que convierte WhatsApp en intake, despacho, seguimiento de visita, garantía y mantenimiento.
- Buyer principal: Dueño o gerente de operación de servicio en sitio
- Problema: Field services falla cuando no clasifica urgencia, no levanta contexto suficiente, no asigna técnico rápido, no da visibilidad de estatus y no convierte servicio puntual en mantenimiento.
- Promesa: Cada mensaje termina en orden de trabajo, visita programada, servicio cerrado o mantenimiento vendido.
- Monetiza: visita diagnóstica, servicio puntual, urgencia, garantía, mantenimiento recurrente, contratos
- Subverticales: HVAC, plomería, electricidad, cerrajería, paneles solares, limpieza especializada, fumigación, jardinería, mantenimiento residencial, seguridad electrónica

### WAOS Professional Intake

- Tier: tier_2
- Tesis: Sistema operativo conversacional para servicios profesionales de alto seguimiento que protege tiempo experto mediante intake, filtro, consulta, documentos y renovación.
- Buyer principal: Socio, director o gerente de intake/comercial
- Problema: Servicios profesionales pierden tiempo caro en leads mal calificados, intake incompleto, asignación débil de especialista, documentos desordenados y consultas no cobradas.
- Promesa: Cada lead termina como no elegible, consulta cobrada, expediente activo o renovación.
- Monetiza: consulta, anticipo, expediente, renovación anual, continuidad del servicio
- Subverticales: legal, migración, contabilidad, fiscal, seguros no complejos, consultoría especializada, notarial, gestoría, compliance ligero, brokers financieros simples

### WAOS Commerce

- Tier: tier_3_guarded
- Tesis: Sistema operativo de commerce y retail conversacional que convierte WhatsApp en descubrimiento, recomendación, pedido, pago, seguimiento y recompra para catálogos simples o medianos.
- Buyer principal: Founder o gerente comercial de marca retail/DTC pequeña
- Problema: Commerce conversacional pierde ventas porque tarda en responder, presenta mal el catálogo, no tiene stock claro, no recomienda bien, no arma carrito y no recupera compras abandonadas.
- Promesa: Cada conversación termina en recomendación, pedido, pago, seguimiento o winback.
- Monetiza: pedido, link de pago, upsell, cross-sell, recompra, drops, bundles
- Subverticales: ropa, streetwear, gorras, tenis, joyería, relojería fashion, accesorios, bolsas, skincare, cosmética, perfumería, regalos, home decor, gadgets, merch, marcas DTC pequeñas
