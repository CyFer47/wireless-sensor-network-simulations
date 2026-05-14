# Troubleshooting MATLAB DB Access

Common fixes:
- JDBC connection fail: confirm the driver jar and the host/IP
- Wrong PostgreSQL host/IP: verify `192.168.1.7`
- PostgreSQL service not running in VMware: restart the DB service in the VM
- Windows cannot access Linux path: use live DB validation instead of file transfer
- Database Toolbox missing: fall back to JDBC-based connection logic
- JDBC driver missing: confirm `postgresql-42.7.10.jar` is on the MATLAB path
- Wrong password: do not store credentials in docs
- Case-sensitive Linux folder issue: use exact paths and avoid assuming case-insensitive matching
- Phase2A CSV package not needed because live DB validation works

If the live DB validation works, prefer the live report path rather than the CSV export path.
