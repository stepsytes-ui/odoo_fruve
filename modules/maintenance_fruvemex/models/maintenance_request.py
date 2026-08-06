from odoo import models, fields, api

class FruveMaintenanceRequest(models.Model):
    _name = 'fruve.maintenance.request'
    _description = 'Solicitud / Orden de Mantenimiento'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    folio = fields.Char(string='Folio', required=True, readonly=True, default='Nuevo', copy=False)

    # Fecha de Registro: Fecha y hora exacta de creación del registro
    fecha_registro = fields.Datetime(
        string='Fecha Registro', 
        default=fields.Datetime.now, 
        readonly=True, 
        required=True
    )


    
    # Se usa self.env.user.id para garantizar que retorne un ID entero válido
    # Registro: Por defecto el usuario actual, pero totalmente editable para seleccionar cualquier usuario/empleado
    user_id = fields.Many2one(
        'res.users', 
        string='Registro', 
        default=lambda self: self.env.user.id, 
        readonly=False, 
        required=True
    )
    
    solicitante_id = fields.Many2one('hr.employee', string='Solicitante', required=True)
    area_id = fields.Many2one('hr.area', string='Área', required=True)
    descripcion = fields.Text(string='Descripción', required=True)
    
    clasificacion = fields.Selection([
        ('correctivo', 'Correctivo'),
        ('preventivo', 'Preventivo'),
        ('mejora', 'Mejora'),
        ('trabajo_temporal', 'Trabajo Temporal')
    ], string='Clasificación', required=True, default='correctivo')
    
    # Comodel actualizado a fruve.maintenance.type
    tipo_id = fields.Many2one('fruve.maintenance.type', string='Tipo', required=True)
    
    # Comodel actualizado a fruve.maintenance.technician
    technician_ids = fields.Many2many(
        'fruve.maintenance.technician',
        'fruve_maintenance_request_technician_rel',
        'request_id',
        'technician_id',
        string='Técnicos'
    )
    
    prioridad = fields.Selection([
        ('inmediata', 'Inmediata'),
        ('urgente', 'Urgente'),
        ('normal', 'Normal'),
        ('plan', 'Plan')
    ], string='Prioridad', default='normal', required=True)

    fecha_asignada = fields.Datetime(string='Fecha Asignada')
    fecha_cierre = fields.Datetime(string='Fecha Cierre')

    # Cálculo automático de horas totales transcurridas entre Fecha Asignada y Fecha Cierre
    horas_totales = fields.Float(
        string='Horas Totales', 
        compute='_compute_horas_totales', 
        store=True, 
        digits=(16, 2)
    )
    
    motivo_no_realizacion_id = fields.Many2one('fruve.maintenance.cancel.reason', string='Motivo de No Realización')
    
    tiempo_extra = fields.Boolean(string='Tiempo Extra', default=False)
    solucion = fields.Text(string='Solución')
    herramientas = fields.Text(string='Herramientas')

    @api.depends('fecha_asignada', 'fecha_cierre')
    def _compute_horas_totales(self):
        for record in self:
            if record.fecha_asignada and record.fecha_cierre:
                # Calcula la diferencia exacta en segundos y la convierte a horas
                diferencia = record.fecha_cierre - record.fecha_asignada
                record.horas_totales = diferencia.total_seconds() / 3600.0
            else:
                record.horas_totales = 0.0
                
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('folio', 'Nuevo') == 'Nuevo':
                vals['folio'] = (
                    self.env['ir.sequence'].next_by_code('fruve.maintenance.request')
                    or self.env['ir.sequence'].next_by_code('maintenance.request')
                    or 'Nuevo'
                )
        return super().create(vals_list)