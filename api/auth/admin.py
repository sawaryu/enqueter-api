from flask_restx import Namespace

"""
*For Admin
"""

admin_ns = Namespace("/admin", description="only for admin user")
