# Registra PyMySQL como conector MySQL para Django (Capítulo VI, sección 6.1.4).
try:
    import pymysql

    # Django 5.x exige que el conector declare versión 2.2.1 o superior de
    # «mysqlclient». PyMySQL es compatible, pero informa una versión antigua
    # (1.4.6), por lo que se ajusta antes de registrarlo.
    pymysql.version_info = (2, 2, 1, 'final', 0)
    pymysql.install_as_MySQLdb()
except ImportError:  # Permite trabajar con SQLite sin tener PyMySQL instalado
    pass
