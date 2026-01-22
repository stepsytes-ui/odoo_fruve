from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.tools.image import image_data_uri

# Importación específica para evitar fallos de carga
try:
    from odoo.addons.hr_attendance.controllers.main import HrAttendance as HrAttendanceController
except ImportError:
    HrAttendanceController = object

class HrAttendanceKioskInherit(HrAttendanceController):
    
    @http.route('/hr_attendance/employees_infos', type="json", auth="public")
    def employees_infos(self, token, limit, offset, domain):
        """
        Extiende la búsqueda de empleados en el kiosco para incluir biometric_id
        """
        company = self._get_company(token)
        if company:
            # Modifica el dominio de búsqueda para incluir biometric_id
            # Si el dominio original busca por nombre, lo extendemos
            modified_domain = []
            for condition in domain:
                if isinstance(condition, (list, tuple)) and len(condition) == 3:
                    field, operator, value = condition
                    # Si están buscando por nombre, agregamos también búsqueda por biometric_id
                    if field == 'name' and operator == 'ilike':
                        modified_domain.append('|')
                        modified_domain.append(condition)
                        modified_domain.append(('biometric_id', 'ilike', value))
                    else:
                        modified_domain.append(condition)
                else:
                    modified_domain.append(condition)
            
            final_domain = expression.AND([modified_domain, [('company_id', '=', company.id)]])
            employees = request.env['hr.employee'].sudo().search_fetch(
                final_domain, 
                ['id', 'display_name', 'job_id', 'biometric_id'],
                limit=limit, 
                offset=offset, 
                order="name, id"
            )
            employees_data = [{
                'id': employee.id,
                'display_name': employee.display_name,
                'job_id': employee.job_id.name,
                'avatar': image_data_uri(employee.avatar_128),
                'biometric_id': employee.biometric_id or ''
            } for employee in employees]
            return {
                'records': employees_data, 
                'length': request.env['hr.employee'].sudo().search_count(final_domain)
            }
        return []