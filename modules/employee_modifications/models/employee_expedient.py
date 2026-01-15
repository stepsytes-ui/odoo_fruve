
from odoo import models, fields, api, exceptions, _
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.osv import expression

class EmployeeExpedient(models.Model):
    _name = 'employee.expedient'
    _description = 'Expediente de Movimientos de Empleados'
    _inherit = ['mail.thread']
    _order = 'fecha_movimiento desc'

    # Campo de relación con el empleado
    employee_id = fields.Many2one(
        'hr.employee', 
        string='Empleado', 
        required=True, 
        ondelete='cascade'
    )

    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        related='employee_id.company_id', 
        store=True, 
        readonly=True, 
        index=True, 
        groups="base.group_multi_company", 
    )

    numero_empleado = fields.Char(
        related='employee_id.biometric_id', 
        string='Número de Empleado', 
        readonly=True, 
        store=True
    )

    genero = fields.Selection(
        related='employee_id.gender',
        string='Género',
        readonly=True,
        store=True
    )
    
    employee_status = fields.Selection(
        related='employee_id.employee_status',
        string='Estado del Empleado',
        readonly=True,
        store=True
    )

    tipo_registro = fields.Selection([
        ('alta', 'Alta'),
        ('baja', 'Baja'),
        ('reingreso', 'Reingreso')
    ], string='Tipo de Registro', default='alta', required=True)
    
    fecha_movimiento = fields.Date(
        string='Fecha de Movimiento', 
        required=True,
        default=fields.Date.today
    )
    
    recontratable = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No'),
        ('n/a', 'N/A'),
    ], string='Recontratable', default='n/a', required=True)
    
    name = fields.Char(
        string='Referencia', 
        compute='_compute_name', 
        store=True
    )
    motivo_baja = fields.Text(string='Motivo/Razón de Baja/Renuncia')
    hoja_renuncia_convenio = fields.Binary(
        string='Hoja de Renuncia/Convenio (PDF)',
        attachment=True,
        required=False,
    )
    nombre_hoja_renuncia = fields.Char(string='Nombre Archivo Renuncia')
    encuesta= fields.Binary(
        string='Encuesta',
        attachment= True,
    )
    nombre_encuesta = fields.Char(string='Nombre Encuesta')

    antiguedad = fields.Char(
        string='Antiguedad',
        compute='_compute_antiguedad_vacaciones',
        store=True
    )

    dias_vacaciones_ley = fields.Integer(
        string='Días de vacaciones',
        compute='_compute_antiguedad_vacaciones',
        store=True
    )

    dias_vacaciones_ajuste = fields.Float(
        string='Ajuste de Días de Vacaciones',
        default=0.0,
        tracking=True,
    )

    dias_vacaciones_utilizados = fields.Float(
        string='Días de Vacaciones Utilizados',
        default=0.0,
        tracking=True
    )

    dias_vacaciones_disponibles = fields.Float(
        string='Días de Vacaciones disponibles',
        compute='_compute_dias_disponibles',
        store=True
    )

    dias_vacaciones_saldo_inicial = fields.Float( 
        string='Días de Vacaciones (Saldo Inicial)',
        compute='_compute_dias_inicial_calculado',
        store=True
    )

    history_ids = fields.One2many(
        'employee.expedient.line', 
        'expedient_id', 
        string='Historial de Fechas'
    )

    @api.depends('employee_id', 'tipo_registro', 'fecha_movimiento')
    def _compute_name(self):
        for record in self:
            employee_name = record.employee_id.name if record.employee_id else 'Nuevo'
            mov_type = dict(record._fields['tipo_registro'].selection).get(record.tipo_registro, '')
            date_str = record.fecha_movimiento.strftime('%Y-%m-%d') if record.fecha_movimiento else ''
            record.name = f"{employee_name} - {mov_type} ({date_str})"
    
    @api.depends('dias_vacaciones_saldo_inicial', 'dias_vacaciones_utilizados')
    def _compute_dias_disponibles(self):
        for record in self:
            record.dias_vacaciones_disponibles = record.dias_vacaciones_saldo_inicial - record.dias_vacaciones_utilizados

    @api.depends('dias_vacaciones_ley', 'dias_vacaciones_ajuste')
    def _compute_dias_inicial_calculado(self):
        for record in self:
            record.dias_vacaciones_saldo_inicial = record.dias_vacaciones_ley + record.dias_vacaciones_ajuste     

    #Función de calculo de antiguedad y días de vacaciones
    @api.depends('employee_id', 'fecha_movimiento')
    def _compute_antiguedad_vacaciones(self):
        TABLA_VACACIONES = [
            (1, 1, 12),
            (2, 2, 14),
            (3, 3, 16),
            (4, 4, 18),
            (5, 5, 20),
            (6, 10, 22),
            (11, 15, 24),
            (16, 20, 26),
            (21, 25, 28),
            (26, 30, 30),
            (31, 35, 32),
        ]

        for record in self:
            fecha_movimiento = record.fecha_movimiento

            if fecha_movimiento and record.employee_id.active:

                hoy = date.today()
                diff = relativedelta(hoy, fecha_movimiento)
                years = diff.years
                months = diff.months
                days = diff.days

                record.antiguedad = f"{years} años, {months} meses y {days} días"

                dias_vacaciones = next(
                    (dias for ini, fin, dias in TABLA_VACACIONES if ini <= years <= fin),
                    0
                )

                record.dias_vacaciones_ley = dias_vacaciones

            else:
                record.antiguedad = "N/A"
                record.dias_vacaciones_ley = 0

    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None): 
        domain = args or []

        active_company_ids = self.env.context.get('allowed_company_ids', False)
        
        if active_company_ids:
            
            company_domain = expression.OR([
                [('company_id', 'in', active_company_ids)],
                [('company_id', '=', False)] 
            ])
            
            domain = expression.AND([domain, company_domain])

        return super(EmployeeExpedient, self)._search(
            domain, 
            offset=offset, 
            limit=limit,  
            order=order
        )
    
    def action_view_disciplinary_records(self):
        self.ensure_one()

        return {
            'name': "Actas Disciplinarias de %s" % self.employee_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'employee.disciplinary.record',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'context': {'default_employee_id': self.employee_id.id},
        }
    
    @api.depends('history_ids.fecha')
    def _compute_latest_movement(self):
        for record in self:
            latest = record.history_ids.filtered(lambda l: l.tipo_movimiento in ['alta', 'reingreso'])
            if latest:
                record.fecha_movimiento = latest[0].fecha
            else:
                record.fecha_movimiento = fields.Date.today()