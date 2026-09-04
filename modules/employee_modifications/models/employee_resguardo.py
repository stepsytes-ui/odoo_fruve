# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeResguardoAsset(models.Model):
    _name = 'employee.resguardo.asset'
    _description = 'Catalogo de Objetos para Resguardo'
    _rec_name = 'nombre'
    _order = 'tipo_resguardo, nombre'

    tipo_resguardo = fields.Selection(
        [
            ('herramienta', 'Herramienta'),
            ('dispositivo', 'Dispositivo movil/laptop'),
            ('general', 'General'),
        ],
        string='Tipo de Resguardo',
        required=True,
        default='general',
    )

    nombre = fields.Char(string='Nombre', required=True)
    color = fields.Char(string='Color')
    funcionando_correctamente = fields.Boolean(string='Funcionando Correctamente', default=True)
    descripcion = fields.Text(string='Descripcion')

    marca = fields.Char(string='Marca')
    modelo = fields.Char(string='Modelo')
    numero_serie = fields.Char(string='Numero de Serie')
    almacenamiento = fields.Char(string='Almacenamiento')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'employee_resguardo_asset_serie_unique',
            'unique(numero_serie)',
            'El numero de serie ya existe para otro objeto de resguardo.',
        ),
    ]

    @api.constrains('tipo_resguardo', 'marca', 'modelo', 'numero_serie', 'almacenamiento')
    def _check_required_fields_for_device(self):
        for record in self:
            if record.tipo_resguardo != 'dispositivo':
                continue

            missing_fields = []
            if not record.marca:
                missing_fields.append(_('Marca'))
            if not record.modelo:
                missing_fields.append(_('Modelo'))
            if not record.numero_serie:
                missing_fields.append(_('Numero de Serie'))
            if not record.almacenamiento:
                missing_fields.append(_('Almacenamiento'))

            if missing_fields:
                raise ValidationError(
                    _('Para tipo Dispositivo movil/laptop faltan campos obligatorios: %s') % ', '.join(missing_fields)
                )


class EmployeeResguardo(models.Model):
    _name = 'employee.resguardo'
    _description = 'Resguardo de Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_entrega desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
        tracking=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True,
    )

    biometric_id = fields.Char(
        string='Numero de Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        related='employee_id.company_id',
        store=True,
        readonly=True,
        index=True,
        groups='base.group_multi_company',
    )

    responsable_rh_id = fields.Many2one(
        'res.users',
        string='Responsable RH',
        default=lambda self: self.env.user,
        tracking=True,
    )

    fecha_entrega = fields.Date(string='Fecha de Entrega', required=True, default=fields.Date.today, tracking=True)
    # fecha_devolucion = fields.Date(string='Fecha de Devolucion', tracking=True)

    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('active', 'Activo'),
            ('partial', 'Parcial'),
            ('returned', 'Devuelto'),
        ],
        string='Estado',
        compute='_compute_state',
        store=True,
        readonly=True,
        tracking=True,
    )

    line_ids = fields.One2many('employee.resguardo.line', 'resguardo_id', string='Checklist de Objetos')

    total_items = fields.Integer(string='Objetos Prestados', compute='_compute_totals', store=True)
    returned_items = fields.Integer(string='Objetos Devueltos', compute='_compute_totals', store=True)

    documento_entrega = fields.Binary(string='Acta de Entrega (PDF)', attachment=True)
    documento_entrega_filename = fields.Char(string='Nombre Documento Entrega')

    documento_devolucion = fields.Binary(string='Acta de Devolucion (PDF)', attachment=True)
    documento_devolucion_filename = fields.Char(string='Nombre Documento Devolucion')

    notas = fields.Text(string='Notas')

    @api.depends('line_ids', 'line_ids.devuelto')
    def _compute_totals(self):
        for record in self:
            record.total_items = len(record.line_ids)
            record.returned_items = len(record.line_ids.filtered('devuelto'))

    @api.depends('line_ids', 'line_ids.devuelto')
    def _compute_state(self):
        for record in self:
            if not record.line_ids:
                record.state = 'draft'
            else:
                returned = len(record.line_ids.filtered('devuelto'))
                total = len(record.line_ids)
                if returned == 0:
                    record.state = 'active'
                elif returned < total:
                    record.state = 'partial'
                else:
                    record.state = 'returned'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('employee.resguardo') or _('Nuevo')
        return super().create(vals_list)

    def action_mark_all_returned(self):
        for record in self:
            for line in record.line_ids.filtered(lambda l: not l.devuelto):
                line.write({'devuelto': True})
            if not record.fecha_devolucion:
                record.fecha_devolucion = fields.Date.today()


class EmployeeResguardoLine(models.Model):
    _name = 'employee.resguardo.line'
    _description = 'Linea de Resguardo de Empleado'
    _order = 'id asc'

    resguardo_id = fields.Many2one('employee.resguardo', string='Resguardo', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='resguardo_id.employee_id', string='Empleado', store=True, readonly=True)

    asset_id = fields.Many2one('employee.resguardo.asset', string='Objeto', required=True)
    quantity_object = fields.Integer(string='Cantidad', required=True, default=1)

    tipo_resguardo = fields.Selection(related='asset_id.tipo_resguardo', string='Tipo', store=True, readonly=True)

    nombre = fields.Char(string='Nombre', related='asset_id.nombre', readonly=True)
    color = fields.Char(string='Color', related='asset_id.color', readonly=True)
    marca = fields.Char(string='Marca', related='asset_id.marca', readonly=True)
    modelo = fields.Char(string='Modelo', related='asset_id.modelo', readonly=True)
    numero_serie = fields.Char(string='Numero de Serie', related='asset_id.numero_serie', readonly=True)
    almacenamiento = fields.Char(string='Almacenamiento', related='asset_id.almacenamiento', readonly=True)

    # funcionando_al_entregar = fields.Boolean(string='Funcionando al Entregar', default=True)
    fecha_entrega = fields.Date(string='Fecha de Entrega/Objeto')
    devuelto = fields.Boolean(string='Devuelto') 
    fecha_devolucion = fields.Date(string='Fecha de Devolucion/Objeto')
    funcionando_al_devolver = fields.Boolean(string='Funcionando al Devolver', default=False)
    observaciones = fields.Text(string='Observaciones')

    @api.constrains('quantity_object')
    def _check_quantity_object_positive(self):
        for record in self:
            if record.quantity_object < 1:
                raise ValidationError(_('La cantidad debe ser mayor a 0.'))

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        return

    @api.onchange('devuelto')
    def _onchange_devuelto(self):
        for record in self:
            if record.devuelto and not record.fecha_devolucion:
                record.fecha_devolucion = fields.Date.today()
            if not record.devuelto:
                record.fecha_devolucion = False
