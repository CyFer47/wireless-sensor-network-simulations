# Test PostgreSQL JDBC Connection

Expected settings:
- Host: `192.168.1.7`
- Port: `5432`
- Database: `wsn_sim`

Safer project-side connection test:

```matlab
test_db_connection
```

Raw MATLAB Database Toolbox example without storing the password in this document:

```matlab
conn = database('wsn_sim','wsn_user','<password>','Vendor','PostgreSQL','Server','192.168.1.7','PortNumber',5432);
isopen(conn)
close(conn)
```

If the project scripts are already configured, prefer `test_db_connection()` because it uses the local project connection logic and avoids exposing credentials.
