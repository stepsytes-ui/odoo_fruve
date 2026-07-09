# -*- coding: utf-8 -*-
from odoo import models, fields, api


class EnfermeriaAccidente(models.Model):
    _name = 'enfermeria.accidente'
    _description = 'Registro de Accidentes'
    _order = 'id desc'

    name = fields.Char(
        string='No. Reporte',
        readonly=True,
        copy=False,
        default='Nuevo',
    )

    # NO. EMP — biometric_id del empleado (relacionado via hr.employee)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='restrict',
    )
    no_emp = fields.Char(
        string='No. EMP',
        related='employee_id.biometric_id',
        store=True,
        readonly=True,
    )
    nombre = fields.Char(
        string='Nombre',
        related='employee_id.name',
        store=True,
        readonly=True,
    )

    # Área del accidente — tomada del modelo hr.area del módulo overtime
    area_id = fields.Many2one(
        'hr.area',
        string='Área del Accidente',
    )

    tipo_causa = fields.Selection(
        selection=[
            ('acto_inseguro', 'Acto Inseguro'),
            ('condicion_insegura', 'Condición Insegura'),
            ('mixto', 'Mixto'),
        ],
        string='Tipo de Causa',
        required=True,
    )

    dia_accidente = fields.Date(
        string='Día del Accidente',
        required=True,
    )

    inicia_st7 = fields.Date(
        string='Inicia con S-T7',
    )

    cierre_st2 = fields.Date(
        string='Cierre con ST-2',
    )

    atencion = fields.Selection(
        selection=[
            ('imss', 'IMSS'),
            ('interno', 'Interno'),
            ('clinica', 'Clínica'),
        ],
        string='Atención',
        required=True,
    )

    riesgo_trabajo_imss = fields.Selection(
        selection=[
            ('si', 'Sí'),
            ('no', 'No'),
        ],
        string='Riesgo de Trabajo por IMSS',
        required=True,
    )

    dias_incapacidad = fields.Integer(
        string='Días de Incapacidad',
        default=0,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('enfermeria.accidente') or 'Nuevo'
        return super().create(vals_list)
