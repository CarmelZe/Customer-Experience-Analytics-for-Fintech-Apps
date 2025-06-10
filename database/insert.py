import oracledb
connection = oracledb.connect(user="SYSTEM", password="oracar123", dsn="")
cursor = connection.cursor()
cursor.execute("INSERT INTO reviews (...) VALUES (...)")
connection.commit()